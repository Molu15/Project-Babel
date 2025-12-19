import unittest
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.translator import TranslationEngine

# Mock classes for event
class MockEvent:
    def __init__(self, name, event_type='down', modifiers=None):
        self.name = name
        self.event_type = event_type
        self.modifiers = modifiers if modifiers else []

class TestTranslationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TranslationEngine()
        # Load the actual config
        config_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'config', 'mappings', 'figma_to_photoshop.json')
        self.engine.load_mapping(config_path)

    def test_duplicate_mapping(self):
        # Input: ctrl+d -> Output: ctrl+j
        event = MockEvent('d', modifiers=['ctrl'])
        result = self.engine.translate(event)
        self.assertEqual(result, 'ctrl+j')

    def test_deselect_mapping(self):
        # Input: esc -> Output: ctrl+d
        event = MockEvent('esc')
        result = self.engine.translate(event)
        self.assertEqual(result, 'ctrl+d')
        
    def test_no_match(self):
        # Input: ctrl+a (not in map)
        event = MockEvent('a', modifiers=['ctrl'])
        result = self.engine.translate(event)
        self.assertIsNone(result)
        
    def test_wrong_modifiers(self):
        # Input: alt+d (should not match ctrl+d)
        event = MockEvent('d', modifiers=['alt'])
        result = self.engine.translate(event)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
