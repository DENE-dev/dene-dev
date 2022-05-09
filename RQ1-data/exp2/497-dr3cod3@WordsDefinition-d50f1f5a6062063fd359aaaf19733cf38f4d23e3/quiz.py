#!/usr/bin/env python3
import random
def get_word_definition(word_list, word_definition):
    word_index = random.randrange(len(word_list))
    word = word_list[word_index]
    definition = word_definition.get(word)
    return(word, definition)


def get_dictionary(rawstring):
    word, definition = rawstring.split(',', 1)
    return (word, definition)
fh = open('Vocabulary_list.csv', 'r')
wd_list = fh.readlines()
#print(wd_list)
wd_set = set(wd_list[1:])
fh = open('Vocabulary_set.csv', 'w')
fh.writelines(wd_set)

word_dict = dict()

for rawstring in wd_set:
    word, definition = get_dictionary(rawstring)
    word_dict[word] = definition
    print(word)


word_list = list(word)

