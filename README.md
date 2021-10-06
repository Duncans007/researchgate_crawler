# researchgate_crawler

To run: use file `researchgate_crawler.py`

Includes a single self-contained classt.
`researchgate_crawler()`

The object only needs to be created with the necessary arguments:
```
crawler = researchgate_crawler(init_url)
#init_url -> string, url to start branching from
```
It will automatically run itself. Can be force-stopped at any point with `ctrl-c` to view output file.

Modifiable interior parameters include:
'''
score_threshold -> int, minimum score threshold required to pull links
max_iter        -> int, maximum number of checked papers
loop_delay      -> int, seconds, stops server from kicking you out
num_papers      -> int, total number of tracked papers
keywords        -> list, strings, keywords for determining scoring
filepath        -> string, path to dump top-scoring URLs **as they are found**
'''
