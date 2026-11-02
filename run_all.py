"""Zero-dependency test runner. No pytest required."""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
loader = unittest.TestLoader()
suite = loader.discover(HERE, pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
