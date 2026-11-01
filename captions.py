"""Short readable subtitle groups; retain every spoken word and its timing."""
def chunks(words, max_words=4, max_chars=30):
    start=0
    while start<len(words):
        end=start+1
        while end<len(words) and end-start<max_words:
            if max_chars is not None and len(' '.join(words[start:end+1]))>max_chars:break
            end+=1
        yield start,words[start:end]
        start=end
