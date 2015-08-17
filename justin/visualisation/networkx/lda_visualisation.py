"""
Visualisation methods for the LDA results
"""
from __future__ import print_function

import SimpleHTTPServer
import SocketServer
import json
import sys

from networkx.readwrite import json_graph
from pandas.core.frame import DataFrame

import networkx as nx
import numpy as np
import pandas as pd
import pylab as plt


def export_docdf_to_cytoscape(infile, sif_out, noa_out):
    """ Exports docdf to a format that can be parsed by cytoscape """

    print("Loading " + infile)
    docdf = pd.read_csv(infile, index_col=0)
    
    df = DataFrame(columns=('parent', 'child', 'score'))    
    i = 0
    docnames = []
    topics = []
    for row_index, row_value in docdf.iterrows():    
        for col_index, col_value in row_value.iteritems():
            if col_value > 0:
                tokens = row_index.split('_')
                docname = str(tokens[0]) + "_" + str(tokens[1])
                topic = col_index
                score = col_value 
                df.loc[i] = [topic, docname, score]
                docnames.append(docname)
                topics.append(topic)
                i += 1
#     unique = set(topics)
#     for u in unique:
#         df.loc[i] = ["ROOT", u, 0]
#         i += 1
                
    print(df)    
    df.to_csv(sif_out, index=False)
    print("Saved to " + sif_out)
    
    f = open(noa_out,'w')
    print("NodeType", file=f)
    for docname in docnames:
        print(docname + " = document", file=f)
    for topic in topics:
        print(topic + " = topic", file=f)
    f.close()    
    print("Saved to " + noa_out)

def _get_docname(row_index):
    tokens = row_index.split('_')
    docname = "doc_"+ str(tokens[0]) + "_" + str(tokens[1])
    return docname

def _get_topicname(col_index):
    topic = "topic_" + str(col_index)
    return topic

def export_docdf_to_gephi(infile, nodes_out, edges_out):
    """ Exports docdf to a format that can be parsed by Gephi """

    print("Loading " + infile)
    docdf = pd.read_csv(infile, index_col=0)

    node_names = set()
    for row_index in docdf.index:
        docname = _get_docname(row_index)
        node_names.add(docname)
    for col_index in docdf.columns:
        topic = _get_topicname(col_index)
        node_names.add(topic)

    nodes = {}
    node_id = 0
    f = open(nodes_out,'w')
    print("Id,Label", file=f)
    for n in node_names:
        nodes[n] = node_id
        print(str(node_id) + "," + n, file=f)        
        node_id += 1
    f.close()    
    print("Saved to " + nodes_out)        
        
    df = DataFrame(columns=('Source', 'Target', 'Weight', 'Type'))    
    i = 0
    for row_index, row_value in docdf.iterrows():    
        for col_index, col_value in row_value.iteritems():
            if col_value > 0:
                docname = _get_docname(row_index)
                topic = _get_topicname(col_index)
                docid = str(nodes[docname])
                topicid = str(nodes[topic])
                weight = "%.3f" % col_value 
                df.loc[i] = [docid, topicid, weight, 'Directed']
                i += 1
                
    print(df)    
    df.to_csv(edges_out, index=False)
    print("Saved to " + edges_out)
    
def get_json_from_docdf(docdf, to_highlight, threshold):

    if to_highlight is None:
        to_highlight = []

    G = nx.Graph()
    node_names = set()
    for row_index in docdf.index:
        docname = _get_docname(row_index)
        node_names.add(docname)
    for col_index in docdf.columns:
        topic = _get_topicname(col_index)
        node_names.add(topic)

    nodes = {}
    node_id = 0
    for n in node_names:
        nodes[n] = node_id
        node_id += 1
        
    for row_index, row_value in docdf.iterrows():    
        for col_index, col_value in row_value.iteritems():
            if col_value > 0:
                docname = _get_docname(row_index)
                topic = _get_topicname(col_index)
                docid = nodes[docname]
                topicid = nodes[topic]
                weight = col_value
                if weight > 0:
                    G.add_edge(docid, topicid, weight=weight)

    for n in node_names:
        node_id = nodes[n]
        if node_id in G:

            # always insert all documents
            if n.startswith('doc'):
                node_group = 1
                node_size = 10
                node_score = 0
                node_type = "square"
                special = False
                if n in to_highlight:
                    node_size = 30
                    special = True
                G.add_node(node_id, name=n, group=node_group, in_degree=0, size=node_size, score=node_score, type=node_type, special=special)

            # for topics, insert only those whose in-degree is above threshold
            elif n.startswith('topic'):
                node_group = 2
                node_size = 60
                node_score = 1
                node_type = "circle"
                in_degree = G.degree(node_id)
                if in_degree >= threshold:
                    if n in to_highlight:
                        special = True                    
                    G.add_node(node_id, name=n, group=node_group, in_degree=in_degree, size=in_degree*5, score=node_score, type=node_type, special=special)
                    print(str(node_id) + ", " + n + " degree=" + str(in_degree) + " added")        
                else:
                    G.remove_node(node_id)
                    print(str(node_id) + ", " + n + " degree=" + str(in_degree) + " removed")   

    # final cleanup, delete all unconnected documents
    unconnected = []
    for n in node_names:
        node_id = nodes[n]
        if node_id in G:
            degree = G.degree(node_id) 
            if n.startswith('doc') and degree == 0:
                unconnected.append(node_id)
    G.remove_nodes_from(unconnected)    

    print("Total nodes = " + str(G.number_of_nodes()))
    print("Total edges = " + str(G.number_of_edges()))

    json_out = json_graph.node_link_data(G) # node-link format to serialize
    return json_out

def export_docdf_to_networkx(infile):
    """ Exports docdf to networkx """

    print("Loading " + infile)
    docdf = pd.read_csv(infile, index_col=0)
    d = get_json_from_docdf(docdf)
    json.dump(d, open('test.json','w'))
    print('Wrote node-link JSON data to test.json') 
    
    PORT = 1234 
    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    print("serving at port " + str(PORT))
    httpd.serve_forever()        

        
def main():
    
    infile = '/home/joewandy/git/metabolomics_tools/justin/notebooks/results/beer3_pos_rel/beer3_pos_rel_docs.csv'
    # infile = '/home/joewandy/git/metabolomics_tools/justin/notebooks/results/urine37_pos_rel/urine37_pos_rel_docs.csv'
    
    # sif_out = '/home/joewandy/git/metabolomics_tools/justin/cytoscape/beer3_pos_docs_cytoscape.sif'
    # noa_out = '/home/joewandy/git/metabolomics_tools/justin/cytoscape/beer3_pos_docs_cytoscape.noa'
    # export_docdf_to_cytoscape(infile, sif_out, noa_out)
    
    # nodes_out = '/home/joewandy/git/metabolomics_tools/justin/visualisation/beer3_pos_nodes.csv'
    # edges_out = '/home/joewandy/git/metabolomics_tools/justin/visualisation/beer3_pos_edges.csv'
    # export_docdf_to_gephi(infile, nodes_out, edges_out)

    export_docdf_to_networkx(infile)
        
if __name__ == "__main__":
    main()