#!/usr/bin/env python3
"""Run each installed regression test ID once; never call an external model."""
import argparse,sys,unittest
from pathlib import Path

def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--agents-root',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.agents_root/'prose'))
    names=['test_reader_layout','test_callout_speech','test_review_efficiency','test_review_flow','test_article_build','test_revision_workflow','test_native_release','test_pipeline','test_scripture','test_handoff','test_quote_layout']
    tests={test.id():test for test in flatten(unittest.TestLoader().loadTestsFromNames(names))}
    return not unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(tests.values())).wasSuccessful()
if __name__=='__main__':raise SystemExit(main())
