from collections import namedtuple
import csv

DatabaseEntry = namedtuple('DatabaseEntry', ['id', 'name', 'formula', 'mass'])
Feature = namedtuple('Feature', ['id', 'mass', 'rt', 'intensity'])
Transformation = namedtuple('Transformation', ['id', 'name', 'sub', 'mul'])

class FileLoader:
    def load_features(self, input_file):
        """ Load peak features """
        features = []
        with open(input_file, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=':')
            next(reader, None)  # skip the headers
            for elements in reader:
                feature = Feature(id=self.num(elements[0]), mass=self.num(elements[1]), \
                                  rt=self.num(elements[2]), intensity=self.num(elements[3]))
                features.append(feature)
        return features

    def load_database(self, database):
        moldb = []
        with open(database, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            for elements in reader:
                mol = DatabaseEntry(id=elements[0], name=elements[1], formula=elements[2], \
                                    mass=self.num(elements[3]))
                moldb.append(mol)
        return moldb
    
    def load_transformation(self, transformation):
        transformations = []
        with open(transformation, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            trans_id = 1
            for elements in reader:
                trans = Transformation(id=trans_id, name=elements[0], sub=self.num(elements[1]), \
                                       mul=self.num(elements[2]))
                transformations.append(trans)
        return transformations        
    
    def num(self, s):
        try:
            return int(s)
        except ValueError:
            return float(s)

class MassBin:
    def __init__(self, start_mass, end_mass):
        self.start_mass = start_mass
        self.end_mass = end_mass
    def get_begin(self):
        return self.start_mass
    def get_end(self):
        return self.end_mass
    def __repr__(self):
        return 'MassBin (' + str(self.start_mass) + ", " + str(self.end_mass) + ')'

class IntervalTree:
    """ 
    Interval tree implementation
    from http://zurb.com/forrst/posts/Interval_Tree_implementation_in_python-e0K
    """
    def __init__(self, intervals):
        self.top_node = self.divide_intervals(intervals)
 
    def divide_intervals(self, intervals):
 
        if not intervals:
            return None
 
        x_center = self.center(intervals)
 
        s_center = []
        s_left = []
        s_right = []
 
        for k in intervals:
            if k.get_end() < x_center:
                s_left.append(k)
            elif k.get_begin() > x_center:
                s_right.append(k)
            else:
                s_center.append(k)
 
        return Node(x_center, s_center, self.divide_intervals(s_left), self.divide_intervals(s_right))
        
 
    def center(self, intervals):
        fs = sort_by_begin(intervals)
        length = len(fs)
 
        return fs[int(length / 2)].get_begin()
 
    def search(self, begin, end=None):
        if end:
            result = []
 
            for j in xrange(begin, end + 1):
                for k in self.search(j):
                    result.append(k)
                result = list(set(result))
            return sort_by_begin(result)
        else:
            return self._search(self.top_node, begin, [])
    def _search(self, node, point, result):
        
        for k in node.s_center:
            if k.get_begin() <= point <= k.get_end():
                result.append(k)
        if point < node.x_center and node.left_node:
            for k in self._search(node.left_node, point, []):
                result.append(k)
        if point > node.x_center and node.right_node:
            for k in self._search(node.right_node, point, []):
                result.append(k)
 
        return list(set(result))
 
class Interval:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end
        
    def get_begin(self):
        return self.begin
    def get_end(self):
        return self.end
 
class Node:
    def __init__(self, x_center, s_center, left_node, right_node):
        self.x_center = x_center
        self.s_center = sort_by_begin(s_center)
        self.left_node = left_node
        self.right_node = right_node
 
def sort_by_begin(intervals):
    return sorted(intervals, key=lambda x: x.get_begin())
