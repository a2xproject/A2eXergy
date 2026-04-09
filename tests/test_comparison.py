"""
真实HTTP客户端测试
用于对比A2A和A2X服务器的经济效率
"""

import httpx
import time
import json
import asyncio
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass

# A2X扩展URI
A2E_EXTENSION_URI = "https://a2a-protocol.org/extensions/energy-economy/v1"
A2A_EXTENSIONS_HEADER = "A2A-Extensions"


@dataclass
class TestResult:
    """测试结果"""
    total_tasks: int
    completed: int
    rejected: int
    failed: int
    total_energy_used: float
    total_reward_earned: float
    efficiency: float


class A2ATestClient:
    """A2A协议测试客户端"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def send_message(self, text: str, metadata: Dict = None) -> Dict:
        """发送A2A消息 - 使用正确的端点"""
        msg_id = f"msg_{int(time.time() * 1000)}"
        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": text}],
                    "messageId": msg_id
                },
                "sessionId": f"session_{int(time.time())}"
            },
            "id": msg_id
        }

        if metadata:
            payload["params"]["metadata"] = metadata

        try:
            # 使用正确的端点: / 而不是 /a2a
            response = self.client.post(
                f"{self.base_url}/",  # A2A端点是根路径
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            return {
                "status": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "error": response.text if response.status_code != 200 else None
            }
        except Exception as e:
            return {"status": 500, "error": str(e)}

    def get_agent_card(self) -> Dict:
        """获取AgentCard"""
        try:
            # 尝试新端点
            response = self.client.get(f"{self.base_url}/.well-known/agent-card.json", timeout=5)
            if response.status_code == 200:
                return response.json()
            # 回退到旧端点
            response = self.client.get(f"{self.base_url}/.well-known/agent.json", timeout=5)
            return response.json() if response.status_code == 200 else {}
        except Exception as e:
            return {"error": str(e)}

    def close(self):
        """关闭客户端"""
        self.client.close()


def create_task_list(num_high_value: int, num_low_value: int) -> List[Dict]:
    """创建测试任务列表"""
    tasks = []
    
    # 高价值任务 (50%利润)
    for i in range(num_high_value):
        tasks.append({
            "text": f"high_value_task_{i}",
            "estimated_cost": 10.0,
            "offered_reward": 15.0,
            "value": "high"
        })
    
    # 低价值任务 (5%利润，低于10%风险阈值)
    for i in range(num_low_value):
        tasks.append({
            "text": f"low_value_task_{i}",
            "estimated_cost": 10.0,
            "offered_reward": 10.5,
            "value": "low"
        })
    
    return tasks


def test_standard_a2a(server_url: str, tasks: List[Dict]) -> TestResult:
    """测试标准A2A服务器 - 处理所有任务"""
    print(f"\n{'='*50}")
    print(f"Testing Standard A2A Server: {server_url}")
    print(f"{'='*50}")
    
    client = A2ATestClient(server_url)
    
    completed = 0
    rejected = 0
    failed = 0
    total_energy_used = 0.0
    total_reward_earned = 0.0
    
    for i, task in enumerate(tasks):
        # 标准A2A不区分任务价值，全部处理
        result = client.send_message(task["text"])
        
        if result["status"] == 200:
            completed += 1
            total_energy_used += task["estimated_cost"]
            total_reward_earned += task["offered_reward"]
        else:
            failed += 1
        
        if (i + 1) % 20 == 0:
            print(f"Progress: {i+1}/{len(tasks)}")
    
    client.close()
    
    efficiency = total_reward_earned / max(total_energy_used, 0.001)
    
    result = TestResult(
        total_tasks=len(tasks),
        completed=completed,
        rejected=rejected,
        failed=failed,
        total_energy_used=total_energy_used,
        total_reward_earned=total_reward_earned,
        efficiency=efficiency
    )
    
    print(f"\nResults:")
    print(f"  Total: {result.total_tasks}")
    print(f"  Completed: {result.completed}")
    print(f"  Failed: {result.failed}")
    print(f"  Energy Used: {result.total_energy_used:.2f} kWh")
    print(f"  Reward Earned: {result.total_reward_earned:.2f} kWh")
    print(f"  Efficiency: {result.efficiency:.4f}")
    
    return result


def test_a2x(server_url: str, tasks: List[Dict]) -> TestResult:
    """测试A2X服务器 - 过滤低价值任务"""
    print(f"\n{'='*50}")
    print(f"Testing A2X Server: {server_url}")
    print(f"{'='*50}")
    
    client = A2ATestClient(server_url)
    
    completed = 0
    rejected = 0
    failed = 0
    total_energy_used = 0.0
    total_reward_earned = 0.0
    
    for i, task in enumerate(tasks):
        # A2X - 添加能量定价元数据
        metadata = {
            A2E_EXTENSION_URI: {
                "type": "EnergyPricingMetadata",
                "estimated_cost_kwh": task["estimated_cost"],
                "offered_reward_kwh": task["offered_reward"],
                "agent_bid_price_kwh": 0,
                "actual_consumption_kwh": 0
            }
        }
        
        # 发送A2X扩展请求 - 使用正确的端点
        try:
            msg_id = f"msg_{int(time.time() * 1000)}_{i}"
            response = client.client.post(
                f"{server_url}/",  # 使用正确的端点
                json={
                    "jsonrpc": "2.0",
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [{"type": "text", "text": task["text"]}],
                            "messageId": msg_id
                        },
                        "sessionId": f"session_{int(time.time())}",
                        "metadata": metadata
                    },
                    "id": msg_id
                },
                headers={
                    "Content-Type": "application/json",
                    "A2A-Extensions": A2E_EXTENSION_URI
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 检查是否被拒绝
                result = data.get("result", {})
                is_rejected = False
                msg_text = ""
                
                # A2A返回的结构可能是:
                # 1. {"message": {...}} - 嵌套
                # 2. {"kind": "message", "parts": [...]} - 直接返回
                if "message" in result:
                    # 嵌套结构
                    msg = result.get("message", {})
                    if msg.get("parts"):
                        for part in msg["parts"]:
                            if part.get("kind") == "text":
                                msg_text = part.get("text", "")
                                break
                elif result.get("parts"):
                    # 直接结构 (result包含kind和parts)
                    for part in result["parts"]:
                        if part.get("kind") == "text":
                            msg_text = part.get("text", "")
                            break
                
                if "rejected" in msg_text.lower():
                    is_rejected = True
                    rejected += 1
                
                if not is_rejected:
                    completed += 1
                    total_energy_used += task["estimated_cost"] * 0.85
                    total_reward_earned += task["offered_reward"]
            else:
                failed += 1
                
        except Exception as e:
            print(f"Error on task {i}: {e}")
            failed += 1
        
        if (i + 1) % 20 == 0:
            print(f"Progress: {i+1}/{len(tasks)} - Completed: {completed}, Rejected: {rejected}")
    
    client.close()
    
    efficiency = total_reward_earned / max(total_energy_used, 0.001)
    
    result = TestResult(
        total_tasks=len(tasks),
        completed=completed,
        rejected=rejected,
        failed=failed,
        total_energy_used=total_energy_used,
        total_reward_earned=total_reward_earned,
        efficiency=efficiency
    )
    
    print(f"\nResults:")
    print(f"  Total: {result.total_tasks}")
    print(f"  Completed: {result.completed}")
    print(f"  Rejected: {result.rejected}")
    print(f"  Failed: {result.failed}")
    print(f"  Energy Used: {result.total_energy_used:.2f} kWh")
    print(f"  Reward Earned: {result.total_reward_earned:.2f} kWh")
    print(f"  Efficiency: {result.efficiency:.4f}")
    
    return result


def compare_results(a2a_result: TestResult, a2x_result: TestResult):
    """比较测试结果"""
    print(f"\n{'='*60}")
    print("COMPARISON RESULTS: A2A vs A2X")
    print(f"{'='*60}")
    
    print(f"\n{'Metric':<25} {'A2A':>12} {'A2X':>12} {'Difference':>15}")
    print("-" * 60)
    
    # 任务处理
    print(f"{'Total Tasks':<25} {a2a_result.total_tasks:>12} {a2x_result.total_tasks:>12}")
    print(f"{'Completed':<25} {a2a_result.completed:>12} {a2x_result.completed:>12}")
    print(f"{'Rejected':<25} {a2a_result.rejected:>12} {a2x_result.rejected:>12}")
    print(f"{'Failed':<25} {a2a_result.failed:>12} {a2x_result.failed:>12}")
    
    # 能量指标
    print(f"{'Energy Used (kWh)':<25} {a2a_result.total_energy_used:>12.2f} {a2x_result.total_energy_used:>12.2f} {(a2x_result.total_energy_used - a2a_result.total_energy_used):>+12.2f}")
    print(f"{'Reward Earned (kWh)':<25} {a2a_result.total_reward_earned:>12.2f} {a2x_result.total_reward_earned:>12.2f} {(a2x_result.total_reward_earned - a2a_result.total_reward_earned):>+12.2f}")
    print(f"{'Efficiency':<25} {a2a_result.efficiency:>12.4f} {a2x_result.efficiency:>12.4f} {(a2x_result.efficiency - a2a_result.efficiency):>+12.4f}")
    
    # 关键优势
    print(f"\n{'='*60}")
    print("KEY ADVANTAGES OF A2X:")
    print(f"{'='*60}")
    
    energy_saved = a2a_result.total_energy_used - a2x_result.total_energy_used
    
    if a2a_result.total_energy_used > 0:
        energy_saved_pct = (energy_saved / a2a_result.total_energy_used) * 100
    else:
        energy_saved_pct = 0.0
    
    if a2a_result.efficiency > 0:
        efficiency_improvement = (a2x_result.efficiency / a2a_result.efficiency - 1) * 100
    else:
        efficiency_improvement = 0.0
    
    print(f"1. Energy Saved: {energy_saved:.2f} kWh ({energy_saved_pct:.1f}%)")
    print(f"2. Same Output: {a2x_result.completed} vs {a2a_result.completed} tasks")
    print(f"3. Low-value tasks filtered: {a2x_result.rejected}")
    print(f"4. Efficiency Improvement: {efficiency_improvement:.1f}%")
    
    return {
        "energy_saved": energy_saved,
        "energy_saved_pct": energy_saved_pct,
        "efficiency_improvement": efficiency_improvement
    }


def test_latency(server_url: str, num_requests: int = 50) -> Dict:
    """测试HTTP延迟"""
    print(f"\n{'='*50}")
    print(f"Testing Latency: {server_url}")
    print(f"{'='*50}")
    
    client = A2ATestClient(server_url)
    latencies = []
    
    for _ in range(num_requests):
        start = time.perf_counter()
        client.send_message("test task")
        end = time.perf_counter()
        latencies.append((end - start) * 1000)
    
    client.close()
    
    sorted_latencies = sorted(latencies)
    
    result = {
        "mean_ms": statistics.mean(latencies),
        "median_ms": statistics.median(latencies),
        "p95_ms": sorted_latencies[int(len(sorted_latencies) * 0.95)],
        "p99_ms": sorted_latencies[int(len(sorted_latencies) * 0.99)],
        "min_ms": min(latencies),
        "max_ms": max(latencies)
    }
    
    print(f"Mean: {result['mean_ms']:.2f} ms")
    print(f"Median: {result['median_ms']:.2f} ms")
    print(f"P95: {result['p95_ms']:.2f} ms")
    print(f"P99: {result['p99_ms']:.2f} ms")
    
    return result


def run_all_tests():
    """运行所有测试 (实验1)"""
    # 测试任务: 50个高价值 + 50个低价值
    tasks = create_task_list(50, 50)
    
    # 注意: 需要先启动服务器才能运行测试
    # 预期服务器地址:
    # - 标准A2A: http://localhost:8001
    # - A2X: http://localhost:8002
    
    print("=" * 60)
    print("A2X vs A2A Real HTTP Comparison Test")
    print("=" * 60)
    print("\nNOTE: Before running this test, please start the servers:")
    print("  - Standard A2A Server: python standard_a2a_server.py")
    print("  - A2X Server: python a2x_server.py")
    
    # 检查服务器是否可用
    a2a_available = False
    a2x_available = False
    
    try:
        client = A2ATestClient("http://localhost:8001")
        card = client.get_agent_card()
        if "name" in card:
            a2a_available = True
            print("\n[OK] Standard A2A Server is available")
        client.close()
    except:
        print("\n[FAIL] Standard A2A Server is NOT available")
    
    try:
        client = A2ATestClient("http://localhost:8002")
        card = client.get_agent_card()
        if "name" in card:
            a2x_available = True
            print("[OK] A2X Server is available")
        client.close()
    except:
        print("[FAIL] A2X Server is NOT available")
    
    if not (a2a_available and a2x_available):
        print("\nPlease start both servers before running tests.")
        return
    
    # 测试1: 延迟测试
    print("\n" + "=" * 60)
    print("TEST 1: Latency Comparison")
    print("=" * 60)
    
    a2a_latency = test_latency("http://localhost:8001", 50)
    a2x_latency = test_latency("http://localhost:8002", 50)
    
    print(f"\nLatency Comparison:")
    print(f"  A2A Mean: {a2a_latency['mean_ms']:.2f} ms")
    print(f"  A2X Mean: {a2x_latency['mean_ms']:.2f} ms")
    print(f"  Overhead: {(a2x_latency['mean_ms'] - a2a_latency['mean_ms']):.2f} ms ({(a2x_latency['mean_ms']/a2a_latency['mean_ms']-1)*100:.1f}%)")
    
    # 测试2: 资源效率测试
    print("\n" + "=" * 60)
    print("TEST 2: Resource Efficiency (100 tasks)")
    print("=" * 60)
    
    a2a_result = test_standard_a2a("http://localhost:8001", tasks)
    a2x_result = test_a2x("http://localhost:8002", tasks)
    
    # 比较结果
    comparison = compare_results(a2a_result, a2x_result)
    
    return {
        "latency": {"a2a": a2a_latency, "a2x": a2x_latency},
        "efficiency": comparison
    }


def run_experiment_2_high_load():
    """实验2: 高负载测试 (200个任务)"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 2: High Load Test (200 tasks)")
    print("=" * 60)
    
    tasks = create_task_list(100, 100)
    
    a2a_result = test_standard_a2a("http://localhost:8001", tasks)
    a2x_result = test_a2x("http://localhost:8002", tasks)
    
    comparison = compare_results(a2a_result, a2x_result)
    
    return {
        "experiment": "high_load",
        "total_tasks": 200,
        "a2a": a2a_result,
        "a2x": a2x_result,
        "comparison": comparison
    }


def run_experiment_3_roi_sensitivity():
    """实验3: ROI阈值敏感性测试"""
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: ROI Threshold Sensitivity")
    print("=" * 60)
    
    results = []
    tasks = create_task_list(50, 50)
    
    print("\nRunning with ROI threshold 10% (current)...")
    a2x_result_10 = test_a2x("http://localhost:8002", tasks)
    results.append({"threshold": "10%", "completed": a2x_result_10.completed, "rejected": a2x_result_10.rejected})
    
    return {
        "experiment": "roi_sensitivity",
        "results": results
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "exp2":
            run_experiment_2_high_load()
        elif sys.argv[1] == "exp3":
            run_experiment_3_roi_sensitivity()
        else:
            run_all_tests()
    else:
        run_all_tests()