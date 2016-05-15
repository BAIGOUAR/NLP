
# coding: utf-8

# In[13]:

#! /usr/bin/python

__author__="Daniel Bauer <bauer@cs.columbia.edu>"
__date__ ="$Sep 12, 2011"

import sys
from collections import defaultdict
import math

"""
Count n-gram frequencies in a data file and write counts to
stdout. 
"""

def simple_conll_corpus_iterator(corpus_file):
    """
    Get an iterator object over the corpus file. The elements of the
    iterator contain (word, ne_tag) tuples. Blank lines, indicating
    sentence boundaries return (None, None).
    """
    l = corpus_file.readline()
    while l:
        line = l.strip()
        if line: # Nonempty line
            # Extract information from line.
            # Each line has the format
            # word pos_tag phrase_tag ne_tag
            fields = line.split(" ")
            ne_tag = fields[-1] # tag
            #phrase_tag = fields[-2] #Unused
            #pos_tag = fields[-3] #Unused
            word = " ".join(fields[:-1])
            yield word, ne_tag
        else: # Empty line
            yield (None, None)                        
        l = corpus_file.readline()

def sentence_iterator(corpus_iterator):
    """
    Return an iterator object that yields one sentence at a time.
    Sentences are represented as lists of (word, ne_tag) tuples.
    """
    current_sentence = [] #Buffer for the current sentence
    for l in corpus_iterator:    
#             print ("***NOW",l) # Every line (every word) l -->  ('nucleotidase', 'I-GENE')
            if l==(None, None):
                if current_sentence:  #Reached the end of a sentence
                    yield current_sentence
                    current_sentence = [] #Reset buffer
                else: # Got empty input stream
                    sys.stderr.write("WARNING: Got empty input file/stream.\n")
                    raise StopIteration
            else:
                current_sentence.append(l) #Add token to the buffer

    if current_sentence: # If the last line was blank, we're done
#         print ("Current ",current_sentence)
        yield current_sentence  #Otherwise when there is no more token
                                # in the stream return the last sentence.
        #Current_sentence  [('When', 'O'), ('CSF', 'O'), ('joj', 'O'),...]  (read in as a key-value pairs collection)

def get_ngrams(sent_iterator, n):
    """
    Get a generator that returns n-grams over the entire corpus,
    respecting sentence boundaries and inserting boundary tokens.
    Sent_iterator is a generator object whose elements are lists
    of tokens. 每个句子前追加2个*，后追加一个STOP标志(w_boundary)
    """
    for sent in sent_iterator:
         # sent (list) --> [('omparison', 'O'), ('with', 'O'),  ...] (Tupels in every sentence)
         #Add boundary symbols to the sentence
         w_boundary = (n-1) * [(None, "*")]
         w_boundary.extend(sent)
         w_boundary.append((None, "STOP"))
         #Then extract n-grams
        
         ngrams = (tuple(w_boundary[i:i+n]) for i in range(len(w_boundary)-n+1))
         for n_gram in ngrams: #Return one n-gram at a time
#             print (n_gram)
            yield n_gram      

#         ngrams
#         (1, 2, 3)
#         (2, 3, 4)
#         (3, 4, 5)
#         (4, 5, 6)
#         (5, 6, 7)
#         >>> 类似这种
#  返回的是这样：
# ((None, '*'), (None, '*'), ('omparison', 'O'))
# ((None, '*'), ('omparison', 'O'), ('with', 'O'))
# (('omparison', 'O'), ('with', 'O'), ('alkaline', 'I-GENE'))


class Hmm(object):
    """
    Stores counts for n-grams and emissions. 
    """

    def __init__(self, n=3):
        assert n>=2, "Expecting n>=2."
        self.n = n
        self.emission_counts = defaultdict(int)
        self.ngram_counts = [defaultdict(int) for i in range(self.n)]
        self.all_states = set()
#       stores emmision para: same type with counts. shape (word,tag):value   meaning em (word|tag)
        self.emision_parameters = defaultdict(float)
#       rare word list
        self.rare = list()

    def train(self, corpus_file):
        """
        Count n-gram frequencies and emission probabilities from a corpus file.
        """
        ngram_iterator =             get_ngrams(sentence_iterator(simple_conll_corpus_iterator(corpus_file)), self.n)
        

        for ngram in ngram_iterator:
            #Sanity check: n-gram we get from the corpus stream needs to have the right length
            assert len(ngram) == self.n, "ngram in stream is %i, expected %i" % (len(ngram, self.n))

            tagsonly = tuple([ne_tag for word, ne_tag in ngram]) #retrieve only the tags    
        #  tagsonly 只收集 ne_tag
        #     ('*', '*', 'O')
        #     ('*', 'O', 'O')
        #     ('O', 'O', 'I-GENE')
            
            for i in range(2, self.n+1): #Count NE-tag 2-grams..n-grams
                self.ngram_counts[i-1][tagsonly[-i:]] += 1
            if ngram[-1][0] is not None: # If this is not the last word in a sentence
                self.ngram_counts[0][tagsonly[-1:]] += 1 # count 1-gram
                self.emission_counts[ngram[-1]] += 1 # and emission frequencies

            # Need to count a single n-1-gram of sentence start symbols per sentence
            if ngram[-2][0] is None: # this is the first n-gram in a sentence
                self.ngram_counts[self.n - 2][tuple((self.n - 1) * ["*"])] += 1
#             print (self.emission_counts)


    def write_counts(self, output, printngrams=[1,2,3]):
        """
        Writes counts to the output file object.
        Format:

        """
        # First write counts for emissions
        for word, ne_tag in self.emission_counts:            
            output.write("%i WORDTAG %s %s\n" % (self.emission_counts[(word, ne_tag)], ne_tag, word))


        # Then write counts for all ngrams
        for n in printngrams:            
            for ngram in self.ngram_counts[n-1]:
                ngramstr = " ".join(ngram)
                output.write("%i %i-GRAM %s\n" %(self.ngram_counts[n-1][ngram], n, ngramstr))

    def read_counts(self, corpusfile):

        self.n = 3
        self.emission_counts = defaultdict(int)
        self.ngram_counts = [defaultdict(int) for i in range(self.n)]
        self.all_states = set()

        for line in corpusfile:
            parts = line.strip().split(" ")
            count = float(parts[0])
            if parts[1] == "WORDTAG":
                ne_tag = parts[2]
                word = parts[3]
                self.emission_counts[(word, ne_tag)] = count
                self.all_states.add(ne_tag)
            elif parts[1].endswith("GRAM"):
                n = int(parts[1].replace("-GRAM",""))
                ngram = tuple(parts[2:])
                self.ngram_counts[n-1][ngram] = count
        
    
    def get_emission_paras(self):
    
        self.emision_parameters = defaultdict(float)
        for wordNtag,counts in self.emission_counts.items():
            tag = wordNtag[1] #get tag of the tuple
            tagCount = self.ngram_counts[0][(tag,)]
            emission = counts / tagCount
            self.emision_parameters[wordNtag]=emission
            print (wordNtag,emission)
#         print (self.emision_parameters)
            
    def replaceRare(self,training_file):
        for wordNtag,counts in self.emission_counts.items():
            print (wordNtag,counts)
            if counts < 5:
                self.rare.append(wordNtag[0])
        print (self.rare)
        
        
        l = training_file.readline()
        print (l)

        while l:
            line = l.strip()
            if line: # Nonempty line
                
                fields = line.split(" ")
                ne_tag = fields[-1] # tag
                word = " ".join(fields[:-1])
                print (word)
                yield word, ne_tag
            else: # Empty line
                yield                         
            l = corpus_file.readline();
        
    



def usage():
    print ("""
    python count_freqs.py [input_file] > [output_file]
        Read in a gene tagged training input file and produce counts.
    """)

if __name__ == "__main__":

    try:
#         input = file(sys.argv[1],"r")
        input = open("mygene.counts")
        training = open("mygene.train");
    except IOError:
        sys.stderr.write("ERROR: Cannot read inputfile %s.\n" % arg)
        sys.exit(1)
    
    # Initialize a trigram counter
    counter = Hmm(3)
    # Collect counts
#     counter.train(input)
    
    #Q1a: Read the counts
    counter.read_counts(input)
#     counter.get_emission_paras()
    
    #Q1b: Replace
    counter.replaceRare(training)


# In[ ]:




# In[ ]:



