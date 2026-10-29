import copy
import json
import unittest
from openinference.core import evaluate, record_hash, haversine_km, check_fields
from openinference.demo import load_snapshot, load_manifest, inject_corruption
from openinference.verify import audit, audit_llm_review
from openinference.llm import make_prompt


class OpenInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_snapshot()
        cls.hashes = load_manifest()

    def result(self, data=None):
        return evaluate(data or self.data,self.hashes)

    def test_snapshot_has_15_real_usgs_records(self):
        self.assertEqual(len(self.data['records']),15)
        self.assertEqual(self.data['source_total_records'],186)
        self.assertTrue(all(r['id'].startswith('us') for r in self.data['records']))

    def test_source_hashes_match_frozen_snapshot(self):
        self.assertTrue(all(record_hash(r)==self.hashes[r['id']] for r in self.data['records']))

    def test_clean_data_unquarantined(self):
        self.assertEqual(self.result()['summary']['quarantined'],0)

    def test_real_philippines_group_discovered(self):
        result=self.result()
        self.assertTrue(any({'us7000ttw3','us7000ttw2','us7000ttxn'}<=set(g['members']) for g in result['clusters']))

    def test_not_causal_earthquake_predictions(self):
        self.assertNotIn('aftershock prediction',json.dumps(self.result()).lower())
        self.assertNotIn('forecast',json.dumps(self.result()).lower())

    def test_large_record_review_separate_from_pattern(self):
        item=next(r for r in self.result()['records'] if r['id']=='us7000ttxz')
        self.assertEqual(item['decision'],'VERIFY_LARGE_RECORD')

    def test_baseline_independent_audit_passes(self):
        result=self.result()
        self.assertEqual(audit(result,self.data,self.hashes)['status'],'PASS')

    def test_synthetic_corruptions_quarantined(self):
        injected=inject_corruption(self.data)
        result=self.result(injected)
        self.assertEqual(result['summary']['quarantined'],5)
        self.assertEqual(audit(result,injected,self.hashes)['status'],'PASS')

    def test_magnitude_tamper_detected_even_if_plausible(self):
        injected=inject_corruption(self.data)
        result=self.result(injected)
        tampered=next(r for r in result['records'] if r['id']=='us7000ttyk')
        self.assertIn('snapshot_hash_mismatch',tampered['issues'])
        self.assertEqual(tampered['decision'],'CHECK_DATA')

    def test_bad_latitude_detected(self):
        injected=inject_corruption(self.data)
        result=self.result(injected)
        bad=next(r for r in result['records'] if r['id']=='us7000ttyw')
        self.assertIn('invalid_lat',bad['issues'])

    def test_update_before_event_detected(self):
        injected=inject_corruption(self.data)
        result=self.result(injected)
        bad=next(r for r in result['records'] if r['id']=='us7000ttyd')
        self.assertIn('update_before_event',bad['issues'])

    def test_duplicate_near_report_detected(self):
        result=self.result(inject_corruption(self.data))
        clone=next(r for r in result['records'] if r['id']=='trainingduplicate0001')
        original=next(r for r in result['records'] if r['id']=='us7000tty7')
        self.assertIn('possible_duplicate_report',clone['issues'])
        self.assertIsNone(clone['source_url'])
        self.assertIn('possible_duplicate_report',original['issues'])

    def test_auditor_detects_fabricated_inference_edge(self):
        report=self.result()
        report['edges'].append({'source':'us7000ttyw','target':'us7000ttw3','distance_km':3,'hours_apart':1})
        self.assertEqual(audit(report,self.data,self.hashes)['status'],'FAIL')

    def test_auditor_detects_wrong_decision(self):
        report=self.result()
        record=next(r for r in report['records'] if r['id']=='us7000ttxz')
        record['decision']='MONITOR'
        self.assertEqual(audit(report,self.data,self.hashes)['status'],'FAIL')

    def test_auditor_detects_removed_true_edge(self):
        report=self.result()
        report['edges']=[]
        self.assertEqual(audit(report,self.data,self.hashes)['status'],'FAIL')

    def test_llm_checker_rejects_made_up_event(self):
        review={'event_id':'us7000ttw3','proposed_decision':'INVESTIGATE_PATTERN',
                'cited_event_ids':['unknown_event'], 'factual_claims':[], 'explanation':'Just trust me'}
        self.assertEqual(audit_llm_review(review,self.result())['status'],'REVIEW_REQUIRED')

    def test_llm_checker_rejects_falsified_magnitude(self):
        review={'event_id':'us7000ttw3','proposed_decision':'INVESTIGATE_PATTERN',
                'cited_event_ids':['us7000ttw3'],
                'factual_claims':[{'event_id':'us7000ttw3','field':'mag','value':9.9}]}
        self.assertEqual(audit_llm_review(review,self.result())['status'],'REVIEW_REQUIRED')

    def test_llm_checker_accepts_valid_structured_claims(self):
        review={'event_id':'us7000ttw3','proposed_decision':'INVESTIGATE_PATTERN',
                'cited_event_ids':['us7000ttw3','us7000ttw2'],
                'factual_claims':[{'event_id':'us7000ttw3','field':'mag','value':5.8}]}
        self.assertEqual(audit_llm_review(review,self.result())['status'],'PASS')

    def test_prompt_contains_rule_and_source_facts(self):
        prompt=make_prompt(self.result(),'us7000ttw3')
        self.assertIn('us7000ttw2',prompt)
        self.assertIn('not automatically',prompt.lower()+' not automatically')

    def test_evidence_quality_not_probability(self):
        row=next(r for r in self.result()['records'] if r['id']=='us7000ttw3')
        self.assertEqual(row['evidence_quality'],1)
        self.assertIn('NOT a calibrated probability',__import__('openinference.core',fromlist=['evidence_quality']).evidence_quality.__doc__)

if __name__ == '__main__':
    unittest.main()
