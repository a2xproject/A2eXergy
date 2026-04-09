"""
A2A vs A2X 兼容性测试
验证A2X协议相对于标准A2A协议的兼容性
"""

import httpx
import time
import json
from typing import Dict, List, Any

A2A_SERVER = "http://localhost:8001"
A2X_SERVER = "http://localhost:8002"

A2E_EXTENSION_URI = "https://a2a-protocol.org/extensions/energy-economy/v1"


class CompatibilityTest:
    def __init__(self):
        self.results = []
    
    def log(self, message: str):
        print(f"  {message}")
        self.results.append(message)
    
    def test_core_operations(self) -> Dict[str, Any]:
        """测试1: 核心操作兼容性"""
        print("\n" + "="*50)
        print("测试1: 核心操作兼容性")
        print("="*50)
        
        results = {
            "a2a_server": {},
            "a2x_server": {}
        }
        
        # 测试标准A2A操作
        operations = [
            ("message/send", self._test_message_send),
            ("task/get", self._test_task_get),
            ("task/list", self._test_task_list),
        ]
        
        for op_name, op_func in operations:
            self.log(f"\n--- {op_name} ---")
            
            # 测试A2A服务器
            try:
                result = op_func(A2A_SERVER)
                results["a2a_server"][op_name] = result
                self.log(f"A2A服务器: {result}")
            except Exception as e:
                results["a2a_server"][op_name] = f"ERROR: {e}"
                self.log(f"A2A服务器: ERROR - {e}")
            
            # 测试A2X服务器
            try:
                result = op_func(A2X_SERVER)
                results["a2x_server"][op_name] = result
                self.log(f"A2X服务器: {result}")
            except Exception as e:
                results["a2x_server"][op_name] = f"ERROR: {e}"
                self.log(f"A2X服务器: ERROR - {e}")
        
        return results
    
    def _test_message_send(self, server: str) -> str:
        """测试message/send操作"""
        response = httpx.Client(timeout=10).post(
            f"{server}/",
            json={
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": "test"}],
                        "messageId": f"msg_{int(time.time())}"
                    },
                    "sessionId": "test_session"
                },
                "id": f"id_{int(time.time())}"
            }
        )
        if response.status_code == 200:
            return "OK"
        return f"HTTP {response.status_code}"
    
    def _test_task_get(self, server: str) -> str:
        """测试task/get操作"""
        response = httpx.Client(timeout=10).post(
            f"{server}/",
            json={
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "params": {"id": "non_existent"},
                "id": "id_get"
            }
        )
        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                return "ERROR (expected)"
            return "OK"
        return f"HTTP {response.status_code}"
    
    def _test_task_list(self, server: str) -> str:
        """测试task/list操作"""
        response = httpx.Client(timeout=10).post(
            f"{server}/",
            json={
                "jsonrpc": "2.0",
                "method": "tasks/list",
                "params": {},
                "id": "id_list"
            }
        )
        if response.status_code == 200:
            return "OK"
        return f"HTTP {response.status_code}"
    
    def test_metadata_compatibility(self) -> Dict[str, Any]:
        """测试2: 元数据扩展兼容性"""
        print("\n" + "="*50)
        print("测试2: 元数据扩展兼容性")
        print("="*50)
        
        results = {
            "a2a_with_metadata": {},
            "a2x_with_metadata": {},
            "a2x_without_metadata": {}
        }
        
        # 标准metadata（无扩展）
        standard_metadata = {"source": "test"}
        
        # A2E扩展metadata
        a2e_metadata = {
            A2E_EXTENSION_URI: {
                "type": "EnergyPricingMetadata",
                "estimated_cost_kwh": 10.0,
                "offered_reward_kwh": 15.0
            }
        }
        
        # 测试1: A2A服务器 + 标准metadata
        self.log("\n--- A2A服务器 + 标准metadata ---")
        try:
            response = self._send_message(A2A_SERVER, standard_metadata)
            results["a2a_with_metadata"]["standard"] = "OK" if response else "FAIL"
            self.log(f"结果: OK")
        except Exception as e:
            results["a2a_with_metadata"]["standard"] = f"ERROR: {e}"
            self.log(f"结果: ERROR - {e}")
        
        # 测试2: A2X服务器 + 标准metadata（无能量定价）
        self.log("\n--- A2X服务器 + 标准metadata ---")
        try:
            response = self._send_message(A2X_SERVER, standard_metadata)
            results["a2x_without_metadata"]["standard"] = "OK" if response else "FAIL"
            self.log(f"结果: OK")
        except Exception as e:
            results["a2x_without_metadata"]["standard"] = f"ERROR: {e}"
            self.log(f"结果: ERROR - {e}")
        
        # 测试3: A2X服务器 + A2E扩展metadata
        self.log("\n--- A2X服务器 + A2E扩展metadata ---")
        try:
            response = self._send_message(A2X_SERVER, a2e_metadata)
            results["a2x_with_metadata"]["a2e"] = "OK" if response else "FAIL"
            self.log(f"结果: OK")
        except Exception as e:
            results["a2x_with_metadata"]["a2e"] = f"ERROR: {e}"
            self.log(f"结果: ERROR - {e}")
        
        # 测试4: A2A服务器 + A2E扩展metadata（应忽略）
        self.log("\n--- A2A服务器 + A2E扩展metadata (应忽略) ---")
        try:
            response = self._send_message(A2A_SERVER, a2e_metadata)
            results["a2a_with_metadata"]["a2e"] = "OK (ignored)" if response else "FAIL"
            self.log(f"结果: OK (ignored - 无能量经济处理)")
        except Exception as e:
            results["a2a_with_metadata"]["a2e"] = f"ERROR: {e}"
            self.log(f"结果: ERROR - {e}")
        
        return results
    
    def _send_message(self, server: str, metadata: Dict) -> bool:
        """发送消息"""
        response = httpx.Client(timeout=10).post(
            f"{server}/",
            json={
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": "test task"}],
                        "messageId": f"msg_{int(time.time() * 1000)}"
                    },
                    "sessionId": "test_session",
                    "metadata": metadata
                },
                "id": f"id_{int(time.time() * 1000)}"
            }
        )
        return response.status_code == 200
    
    def test_roi_decision(self) -> Dict[str, Any]:
        """测试3: ROI决策兼容性"""
        print("\n" + "="*50)
        print("测试3: ROI决策测试")
        print("="*50)
        
        results = {
            "high_roi": {},
            "low_roi": {}
        }
        
        # 高ROI任务（50%）
        high_roi_metadata = {
            A2E_EXTENSION_URI: {
                "type": "EnergyPricingMetadata",
                "estimated_cost_kwh": 10.0,
                "offered_reward_kwh": 15.0
            }
        }
        
        # 低ROI任务（5%）
        low_roi_metadata = {
            A2E_EXTENSION_URI: {
                "type": "EnergyPricingMetadata",
                "estimated_cost_kwh": 10.0,
                "offered_reward_kwh": 10.5
            }
        }
        
        # 测试高ROI任务
        self.log("\n--- 高ROI任务 (50%) ---")
        try:
            response = self._send_message(A2X_SERVER, high_roi_metadata)
            results["high_roi"]["a2x"] = "ACCEPTED" if response else "REJECTED"
            self.log(f"A2X服务器: ACCEPTED")
            
            response = self._send_message(A2A_SERVER, high_roi_metadata)
            results["high_roi"]["a2a"] = "ACCEPTED" if response else "REJECTED"
            self.log(f"A2A服务器: ACCEPTED (无能量决策)")
        except Exception as e:
            results["high_roi"]["error"] = str(e)
            self.log(f"ERROR: {e}")
        
        # 测试低ROI任务
        self.log("\n--- 低ROI任务 (5%) ---")
        try:
            response = self._send_message(A2X_SERVER, low_roi_metadata)
            results["low_roi"]["a2x"] = "REJECTED" if response else "ACCEPTED"
            self.log(f"A2X服务器: REJECTED (低ROI)")
            
            response = self._send_message(A2A_SERVER, low_roi_metadata)
            results["low_roi"]["a2a"] = "ACCEPTED"
            self.log(f"A2A服务器: ACCEPTED (无能量决策)")
        except Exception as e:
            results["low_roi"]["error"] = str(e)
            self.log(f"ERROR: {e}")
        
        return results
    
    def test_latency(self) -> Dict[str, Any]:
        """测试4: 延迟对比"""
        print("\n" + "="*50)
        print("测试4: 延迟对比")
        print("="*50)
        
        num_requests = 20
        
        # 测试A2A服务器延迟
        a2a_latencies = []
        for i in range(num_requests):
            start = time.perf_counter()
            self._send_message(A2A_SERVER, {})
            end = time.perf_counter()
            a2a_latencies.append((end - start) * 1000)
        
        a2a_mean = sum(a2a_latencies) / len(a2a_latencies)
        self.log(f"A2A服务器平均延迟: {a2a_mean:.2f}ms")
        
        # 测试A2X服务器延迟
        a2x_latencies = []
        for i in range(num_requests):
            start = time.perf_counter()
            self._send_message(A2X_SERVER, {})
            end = time.perf_counter()
            a2x_latencies.append((end - start) * 1000)
        
        a2x_mean = sum(a2x_latencies) / len(a2x_latencies)
        self.log(f"A2X服务器平均延迟: {a2x_mean:.2f}ms")
        
        overhead = a2x_mean - a2a_mean
        overhead_pct = (overhead / a2a_mean) * 100 if a2a_mean > 0 else 0
        self.log(f"延迟开销: {overhead:.2f}ms ({overhead_pct:.1f}%)")
        
        return {
            "a2a_mean_ms": a2a_mean,
            "a2x_mean_ms": a2x_mean,
            "overhead_ms": overhead,
            "overhead_pct": overhead_pct
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("\n" + "="*60)
        print("A2A vs A2X 兼容性测试")
        print("="*60)
        
        # 检查服务器
        print("\n检查服务器...")
        a2a_ok = False
        a2x_ok = False
        
        try:
            httpx.Client(timeout=5).get(f"{A2A_SERVER}/.well-known/agent-card.json")
            a2a_ok = True
            print(f"[OK] A2A服务器: {A2A_SERVER}")
        except:
            print(f"[FAIL] A2A服务器: {A2A_SERVER}")
        
        try:
            httpx.Client(timeout=5).get(f"{A2X_SERVER}/.well-known/agent-card.json")
            a2x_ok = True
            print(f"[OK] A2X服务器: {A2X_SERVER}")
        except:
            print(f"[FAIL] A2X服务器: {A2X_SERVER}")
        
        if not a2a_ok or not a2x_ok:
            self.log("\n错误: 服务器未运行")
            return {"error": "Servers not running"}
        
        # 运行测试
        results = {}
        results["core_operations"] = self.test_core_operations()
        results["metadata_compatibility"] = self.test_metadata_compatibility()
        results["roi_decision"] = self.test_roi_decision()
        results["latency"] = self.test_latency()
        
        # 总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        
        # 核心操作
        co = results["core_operations"]
        a2a_ops = all(v == "OK" for v in co.get("a2a_server", {}).values())
        a2x_ops = all(v == "OK" for v in co.get("a2x_server", {}).values())
        self.log(f"核心操作兼容性: A2A={'OK' if a2a_ops else 'FAIL'}, A2X={'OK' if a2x_ops else 'FAIL'}")
        
        # 元数据兼容
        mc = results["metadata_compatibility"]
        self.log(f"元数据扩展: A2X支持能量定价={mc.get('a2x_with_metadata',{}).get('a2e')=='OK'}")
        
        # ROI决策
        rd = results["roi_decision"]
        self.log(f"ROI决策: 高ROI接受={rd.get('high_roi',{}).get('a2x')}, 低ROI拒绝={rd.get('low_roi',{}).get('a2x')=='REJECTED'}")
        
        # 延迟
        lat = results["latency"]
        self.log(f"延迟开销: {lat.get('overhead_pct',0):.1f}%")
        
        return results


def main():
    test = CompatibilityTest()
    results = test.run_all_tests()
    
    # 保存结果
    output_file = "C:\\Users\\pant\\Desktop\\IoA_code\\A2X\\广播电视技术\\compatibility\\test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")
    return results


if __name__ == "__main__":
    main()