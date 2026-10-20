import sys, unittest
sys.path.insert(0, r'D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_基线复现隔离工作_20261018\src'); sys.path.insert(0, r'D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_基线复现隔离工作_20261018\tests')
import adapters.registry as registry
registry.ORDER = tuple(m for m in registry.ORDER if m != 'CSTAR')
loader = unittest.TestLoader()
suite = unittest.TestSuite([loader.loadTestsFromName(n) for n in
    ('test_edge_cases','test_exact_and_connector','test_contract_and_identity','test_audit_negative','test_epsilon_handtrace')])
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
