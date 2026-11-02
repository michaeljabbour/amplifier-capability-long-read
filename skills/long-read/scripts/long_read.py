#!/usr/bin/env python3
"""Bounded extractive search with resumable jobs; no generated code or model calls."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

FORMAT = 'long-read-job/1'
MAX_BYTES = 8_000_000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def chunks(text, size=8000, overlap=300):
    if type(size) is not int or type(overlap) is not int or not 200 <= size <= 50000 or not 0 <= overlap < size:
        raise ValueError('Chunk size must be 200..50000 characters and overlap smaller than size')
    start = 0
    while start < len(text):
        end = min(len(text), start+size)
        yield {'start': start, 'end': end, 'line_start': text.count('\n', 0, start)+1,
               'line_end': text.count('\n', 0, end)+1, 'text': text[start:end]}
        if end == len(text): break
        start = end-overlap


def read_source(path):
    with Path(path).open('rb') as f: data = f.read(MAX_BYTES+1)
    if len(data) > MAX_BYTES: raise ValueError('Input exceeds 8 MB; partition it explicitly before creating a job')
    return data, data.decode('utf-8')


def create_job(path, query, size=8000, overlap=300):
    if type(query) is not str or not re.findall(r'\w+',query): raise ValueError('A query needs searchable words or identifiers')
    data,text = read_source(path)
    parts = list(chunks(text,size,overlap))
    return {'format': FORMAT, 'source': str(Path(path).resolve()), 'source_sha256': digest(data),
            'query': query, 'chunk_chars': size, 'overlap': overlap,
            'next_chunk': 0, 'total_chunks': len(parts), 'hits': [], 'complete': False}


def advance(job, budget=100, limit=8):
    if type(job) is not dict or job.get('format') != FORMAT or type(budget) is not int or type(limit) is not int or not 1 <= budget <= 1000 or not 1 <= limit <= 50:
        raise ValueError('Invalid job format, chunk budget (1..1000), or result limit (1..50)')
    if not {'source', 'source_sha256', 'query', 'chunk_chars', 'overlap', 'next_chunk', 'total_chunks', 'hits'} <= job.keys():
        raise ValueError('Incomplete saved job; create a new job or restore the complete saved state')
    if type(job['source']) is not str or not job['source'].strip() or type(job['source_sha256']) is not str or not re.fullmatch(r'[0-9a-f]{64}', job['source_sha256']):
        raise ValueError('Corrupt saved source identity')
    if type(job['query']) is not str or not re.findall(r'\w+', job['query']):
        raise ValueError('Corrupt saved query')
    if type(job['total_chunks']) is not int or type(job['next_chunk']) is not int:
        raise ValueError('Corrupt job cursor')
    if 'result_limit' in job and type(job['result_limit']) is not int:
        raise ValueError('Corrupt saved result limit')
    if 'result_limit' in job and job['result_limit'] != limit:
        raise ValueError('Result limit is frozen for a job; create a new job to change it')
    data,text = read_source(job['source'])
    if digest(data) != job['source_sha256']:
        raise ValueError('Source changed; create a new job. Old evidence is retained unchanged.')
    parts = list(chunks(text,job['chunk_chars'],job['overlap']))
    if job['total_chunks'] != len(parts) or not 0 <= job['next_chunk'] <= len(parts):
        raise ValueError('Corrupt job cursor')
    terms = set(re.findall(r'\w+',job['query'].casefold()))
    # A resume file is editable. Recheck retained evidence against the source
    # before trusting or mutating it, even when the source hash still matches.
    hits = job.get('hits')
    if not terms or not isinstance(hits,list) or len(hits) > limit:
        raise ValueError('Corrupt retained evidence')
    seen = set()
    for hit in hits:
        i = hit.get('chunk') if isinstance(hit,dict) else None
        if type(i) is not int or not 0 <= i < job['next_chunk'] or i in seen:
            raise ValueError('Corrupt retained evidence')
        c = parts[i]
        score = len(terms & set(re.findall(r'\w+',c['text'].casefold())))
        if not score or hit != dict(c,chunk=i,score=score):
            raise ValueError('Retained evidence does not match the source and query')
        seen.add(i)
    job['result_limit'] = limit
    end = min(len(parts), job['next_chunk']+budget)
    for i in range(job['next_chunk'],end):
        c = parts[i]
        score = len(terms & set(re.findall(r'\w+',c['text'].casefold())))
        if score:
            # Exact text, offsets and line references; no unsupported synthesized answer.
            job['hits'].append(dict(c,chunk=i,score=score))
    job['hits'] = sorted(job['hits'],key=lambda h:(-h['score'],h['chunk']))[:limit]
    job['next_chunk'] = end
    job['complete'] = end == len(parts)
    job['status'] = 'searched-all-chunks' if job['complete'] else 'partial-chunk-budget'
    job['answer_type'] = 'extractive-evidence; human/host synthesis required'
    return job


def save(path, job, exclusive=False):
    path = Path(path)
    text = json.dumps(job,ensure_ascii=False,indent=2)+'\n'
    if exclusive:
        with path.open('x',encoding='utf-8') as f: f.write(text)
    else:
        fd,tmp = tempfile.mkstemp(dir=path.parent,prefix='.long-read-')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f: f.write(text); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='mode',required=True)
    q=sub.add_parser('search'); q.add_argument('source',type=Path); q.add_argument('--query',required=True); q.add_argument('--job',type=Path); q.add_argument('--chunk-chars',type=int,default=8000); q.add_argument('--overlap',type=int,default=300)
    q=sub.add_parser('resume'); q.add_argument('job',type=Path)
    for q in sub.choices.values(): q.add_argument('--chunk-budget',type=int,default=100); q.add_argument('--limit',type=int,default=8)
    a=p.parse_args(argv)
    try:
        if a.mode=='search':
            if a.job and a.job.exists(): raise ValueError('Job already exists; use resume or choose another output')
            job=create_job(a.source,a.query,a.chunk_chars,a.overlap)
        else: job=json.loads(a.job.read_text())
        advance(job,a.chunk_budget,a.limit)
        if a.job: save(a.job,job,exclusive=a.mode=='search')
        print(json.dumps(job,ensure_ascii=False,indent=2)); return 0
    except (ValueError,OSError,KeyError) as e: p.exit(2,f'{type(e).__name__}: {e}\n')

if __name__=='__main__': raise SystemExit(main())
