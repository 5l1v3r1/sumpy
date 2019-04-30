#!/usr/bin/python3

import sys
import os
import random
import datetime

import sumpy

oracle_code = """
// Given the vector with id=`id`, return a list of
// other vectors which cosine similarity to the reference
// one is greater or equal than the threshold.
// Results are given as a dictionary of :
//      `vector_id => similarity`
function findSimilar(id, threshold) {
    var v = records.Find(id);
    if( v.IsNull() == true ) {
        return ctx.Error("vector " + id + " not found.");
    }

    var results = {};
    var all = records.AllBut(v)
    var num = all.length;    
        
    for( var i = 0; i < num; ++i ) {
        var record = all[i];
        var similarity = v.Cosine(record);
        if( similarity >= threshold ) {
           results[record.ID] = similarity
        }
    }

    return results;
}
"""

def timer_start():
    global start
    sys.stdout.flush()
    start = datetime.datetime.now()

def timer_stop(with_avg=True):
    global start, end, index
    end = datetime.datetime.now()
    diff = end - start
    elapsed_ms = (diff.days * 86400000) + (diff.seconds * 1000) + (diff.microseconds / 1000)
    if with_avg:
        print("%d ms / %.2fms avg" % ( elapsed_ms, float(elapsed_ms) / float(len(index)) ))
    else:
        print("%d ms" % elapsed_ms)

if __name__ == '__main__':
    start = 0
    end = 0
    num_rows = 300
    num_columns = 100
    index = {}

    client = sumpy.Client('localhost:50051', '/etc/sumd/creds/cert.pem')

    # STEP 1: send the oracle code to the server and get its id
    oracle_id = client.define_oracle_code('findSimilar', oracle_code)

    # STEP 2: generate `num_rows` vectors of `num_columns` columns
    # each and ask the server to store them
    print("%d CREATE ops : " % num_rows, end='')
    timer_start()
    for row in range (0, num_rows):
        record = client.create_record({"some": "meta data"}, [random.uniform(0,100) for i in range(0, num_columns)])
        index[record.id] = record
    timer_stop()

    # STEP 2.1: just benchmark READ operations
    print("%d READ ops   : " % num_rows, end='')
    timer_start()
    for ident, record in index.items():
        got = client.read_record(ident)
        assert(record == got)
    timer_stop()
    
    # STEP 3: for every vector, query the oracle to get a list
    # of vectors that have a big cosine similarity
    print("%d CALL ops   : " % num_rows, end='')
    timer_start()
    for ident, record in index.items():
        neighbours = client.invoke_oracle(oracle_id, (ident, 0.81))
        index[ident] = {
            'record': record,
            'neighbours': neighbours,
        }
    timer_stop()

    # STEP 4: remove all, fin.
    print("%d DEL ops    : " % num_rows, end='')
    timer_start()
    for ident, record in index.items():
        client.delete_record(ident)
    timer_stop()

    """ Uncomment to print results ^_^

    print 

    for ident, obj in index.iteritems():
        n = len(obj['neighbours'])
        if n > 0:
            print("Vector %s has %d neighbours with a cosine similarity >= than %f" % ( ident, n, 0.81 ))
    """
