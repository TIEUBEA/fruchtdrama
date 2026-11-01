import unittest
import captions

class CaptionsTests(unittest.TestCase):
    def test_long_german_words_and_french_accents_keep_order_and_timing_offsets(self):
        words="Die Supermarktkassiererin zeigt überraschend die Überwachungskamera près de l’entrée".split()
        groups=list(captions.chunks(words))
        self.assertEqual([w for _,group in groups for w in group],words)
        for start,group in groups:
            self.assertEqual(words[start:start+len(group)],group)
            self.assertLessEqual(len(group),4)
            self.assertTrue(len(' '.join(group))<=30 or len(group)==1)
        self.assertEqual(groups[-1][0]+len(groups[-1][1]),len(words))

    def test_old_jobs_keep_five_word_groups(self):
        self.assertEqual(list(captions.chunks('one two three four five six'.split(),5,None)),
                         [(0,['one','two','three','four','five']),(5,['six'])])

    def test_empty_and_one_long_word(self):
        self.assertEqual(list(captions.chunks([])),[])
        self.assertEqual(list(captions.chunks(['X'*40])),[(0,['X'*40])])
