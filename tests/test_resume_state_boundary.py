"""Exposed malformed-state regressions; not semantic retrieval outcomes."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/long-read/scripts/long_read.py'
spec = importlib.util.spec_from_file_location('resume_boundary_long_read', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ResumeStateBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.txt'
        self.source.write_text('alpha evidence\n' * 80)
        self.job = module.create_job(self.source, 'alpha', size=200, overlap=10)

    def test_malformed_header_rejected_before_mutation(self):
        for field, value in [('next_chunk', True), ('total_chunks', True),
                             ('chunk_chars', '200'), ('chunk_chars', 200.0),
                             ('overlap', False), ('query', []), ('source', []),
                             ('source_sha256', None), ('result_limit', True)]:
            with self.subTest(field=field, value=value):
                job = copy.deepcopy(self.job)
                job[field] = value
                before = copy.deepcopy(job)
                with self.assertRaises(ValueError):
                    module.advance(job)
                self.assertEqual(job, before)

    def test_numeric_arguments_require_actual_integers(self):
        for key, value in [('budget', True), ('budget', 1.0), ('limit', True), ('limit', 1.0)]:
            with self.subTest(key=key, value=value):
                job = copy.deepcopy(self.job)
                with self.assertRaises(ValueError):
                    module.advance(job, **{key: value})
                self.assertEqual(job, self.job)

    def test_invalid_json_shape_is_an_actionable_cli_error(self):
        for value in [[], None, True, {'format': 'long-read-job/1'}]:
            with self.subTest(shape=type(value).__name__):
                path = self.root / 'job.json'
                path.write_text(json.dumps(value))
                prior = path.read_bytes()
                result = subprocess.run([sys.executable, '-B', str(SCRIPT), 'resume', str(path)], capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn(b'Traceback', result.stderr)
                self.assertEqual(path.read_bytes(), prior)

    def test_valid_search_and_resume_still_preserve_exact_evidence(self):
        job = copy.deepcopy(self.job)
        module.advance(job, budget=1)
        self.assertFalse(job['complete'])
        while not job['complete']:
            module.advance(job, budget=2)
        text = self.source.read_text()
        self.assertTrue(job['hits'])
        for hit in job['hits']:
            self.assertEqual(text[hit['start']:hit['end']], hit['text'])


if __name__ == '__main__':
    unittest.main()
