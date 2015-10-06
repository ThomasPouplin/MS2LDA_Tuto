import itertools
from operator import attrgetter
from operator import itemgetter
import sys
import time

from discretisation.continuous_mass_clusterer import ContinuousVB
from discretisation.discrete_mass_clusterer import DiscreteVB
from discretisation.models import HyperPars, Feature, PeakData
from discretisation.plotting import ClusterPlotter
from discretisation.preprocessing import FileLoader
import discretisation.utils as utils
from dp_rt_clusterer import DpMixtureGibbs
import numpy as np
import pylab as plt
import scipy.sparse as sp


def plot_hist(mapping, filename, mass_tol, rt_tol):
    no_trans = (mapping > 0).sum(1)
    mini_hist = []
    for i in np.arange(10) + 1:
        mini_hist.append((no_trans == i).sum())
    print 'mini_hist ' + str(mini_hist)
    plt.figure()
    plt.subplot(1, 2, 1)
    plt.bar(np.arange(10) + 1, mini_hist)
    title = 'Binning -- MASS_TOL ' + str(mass_tol) + ', RT_TOL ' + str(rt_tol)
    plt.title(title)
    plt.subplot(1, 2, 2)
    plt.spy(mapping, markersize=1)
    plt.title('possible')
    plt.suptitle(filename)
    plt.show()     
    
def annotate(annotations, feature, msg):
    if feature in annotations:
        current_msg = annotations[feature]
        annotations[feature] = current_msg + " " + msg
    else:
        annotations[feature] = msg
    
def get_transformation_map(transformations):
    tmap = {}
    t = 1
    for trans in transformations:
        tmap[t] = trans
        t += 1
    return tmap

def find_same_top_id(key, items):
    indices = []
    results = []
    for a in range(len(items)):
        check = items[a]
        if key.top_id == check.top_id:
            indices.append(a)
            results.append(check)
    return indices, results

def match_features(members):
    results = []
    if len(members) == 1:
        # just singleton things
        features = members[0].features
        for f in features:
            tup = (f, )
            results.append(tup)                        
    else:
        # need to match across the same bins
        processed = set()
        for bb1 in members:
            features1 = bb1.features
            for f1 in features1:
                if f1 in processed:
                    continue
                # find features in other bins that are the closest in mass to f1
                temp = []
                temp.append(f1)
                processed.add(f1)
                for bb2 in members:
                    if bb1.origin == bb2.origin:
                        continue
                    else:
                        features2 = bb2.features
                        closest = None
                        min_diff = float('inf')
                        for f2 in features2:
                            if f2 in processed:
                                continue
                            diff = abs(f1.mass - f2.mass)
                            if diff < min_diff:
                                min_diff = diff
                                closest = f2
                        if closest is not None:
                            temp.append(closest)
                            processed.add(closest)
                tup = tuple(temp)
                results.append(tup)  
    return results
    
start = time.time()

database = '../discretisation/database/std1_mols.csv'
transformation = '../discretisation/mulsubs/mulsub2.txt'
input_file = './input/std1_csv_2'

binning_mass_tol = 2.0                 # mass tolerance in ppm when binning
binning_rt_tol = 5.0                   # rt tolerance in seconds when binning
within_file_rt_sd = 2.5                # standard deviation of each cluster when clustering by precursor masses in a single file
across_file_rt_sd = 10.0               # standard deviation of mixture component when clustering by RT across files
alpha_mass = 100.0                     # concentration parameter for precursor mass clustering
alpha_rt = 100.0                       # concentration parameter for DP mixture on RT
t = 0.50                               # threshold for cluster membership for precursor mass clustering
limit_n = 3600                         # the number of features to load per file to make debugging easier, -1 to load all

mass_clustering_n_iterations = 20      # no. of iterations for VB precursor clustering
rt_clustering_nsamps = 20              # no. of total samples for Gibbs RT clustering
rt_clustering_burnin = 10              # no. of burn-in samples for Gibbs RT clustering
    
# First stage clustering. 
# Here we cluster peak features by their precursor masses to the common bins shared across files.
loader = FileLoader()
data_list = loader.load_model_input(input_file, database, transformation, binning_mass_tol, binning_rt_tol, limit_n=limit_n)
transformations = data_list[0].transformations
tmap = get_transformation_map(transformations)
all_bins = []
posterior_bin_rts = []    
posterior_bin_masses = []
annotations = {}

file_bins = []
file_post_rts = []

for j in range(len(data_list)):

    # run precursor mass clustering
    peak_data = data_list[j]
    plot_hist(peak_data.possible, input_file, binning_mass_tol, binning_rt_tol)
    print "Clustering file " + str(j) + " by precursor masses"
    hp = HyperPars()
    hp.rt_prec = 1.0/(within_file_rt_sd*within_file_rt_sd)
    hp.alpha = alpha_mass
    continuous = ContinuousVB(peak_data, hp)
    continuous.n_iterations = mass_clustering_n_iterations
    print continuous
    continuous.run()

    # pick the non-empty bins for the second stage clustering
    cluster_membership = (continuous.Z>t)
    s = cluster_membership.sum(0)
    nnz_idx = s.nonzero()[1]  
    nnz_idx = np.squeeze(np.asarray(nnz_idx)) # flatten the thing

    # find the non-empty bins
    bins = [peak_data.bins[a] for a in nnz_idx]
    print "Non-empty bins=" + str(len(bins))
    all_bins.extend(bins)
    file_bins.append(bins)

    # find the non-empty bins' posterior RT values
    bin_rts = continuous.cluster_rt_mean[nnz_idx]
    plt.figure()
    plt.plot(bin_rts, '.b')
    plt.title("Posterior RT values for file " + str(j))
    plt.xlabel("Non-empty bins")
    plt.ylabel("RT")
    plt.show()
    bin_rts = bin_rts.ravel().tolist()
    posterior_bin_rts.extend(bin_rts)
    file_post_rts.append(bin_rts)
    bin_masses = continuous.cluster_mass_mean[nnz_idx]    
    posterior_bin_masses.extend(bin_masses)

    # make some plots
    cp = ClusterPlotter(peak_data, continuous)
    cp.summary(file_idx=j)
    # cp.plot_biggest(3)        

    # assign peaks into their respective bins, 
    # this makes it easier when matching peaks across the same bins later
    # note: a peak can belong to multiple bins, depending on the choice of threshold t
    cx = cluster_membership.tocoo()
    for i,j,v in itertools.izip(cx.row, cx.col, cx.data):
        f = peak_data.features[i]
        bb = peak_data.bins[j] # copy of the common bin specific to file j
        bb.add_feature(f)    
        # annotate each feature by its precursor mass & adduct type probabilities, for reporting later
        bin_prob = continuous.Z[i, j]
        trans_idx = continuous.possible[i, j]
        transformed_value = continuous.transformed[i, j]
        transformation = tmap[trans_idx]
        msg = "{:s}@{:3.5f} prob={:.2f}".format(transformation.name, transformed_value, bin_prob)            
        annotate(annotations, f, msg)            
    
first_bins = file_bins[0]
first_rts = file_post_rts[0]
second_bins = file_bins[1]
second_rts = file_post_rts[1]
xs = []
ys = []
for j1 in range(len(first_bins)):
    bin1 = first_bins[j1]
    j2s, bin2s = find_same_top_id(bin1, second_bins)
    for j2 in j2s:        
        rt1 = first_rts[j1]
        rt2 = second_rts[j2]
        xs.append(rt1)
        ys.append(rt2)

plt.figure()
plt.plot(np.array(xs), np.array(ys), '.b')
plt.xlabel("File 0")
plt.ylabel("File 1")
plt.title("Bin-vs-bin posterior RTs")
plt.show()

sizes = []
for bin1 in first_bins:
    sizes.append(bin1.get_features_count())
plt.figure()
plt.plot(np.array(sizes), 'r.')
sizes = []
for bin2 in second_bins:
    sizes.append(bin2.get_features_count())
plt.plot(np.array(sizes), 'g.')
plt.title("Bin sizes in file 0 & 1")
plt.xlabel("Bins")
plt.ylabel("Sizes")
plt.show()
        
# Second-stage clustering
print "Second stage clustering"
N = len(all_bins)
assert N == len(posterior_bin_rts)

hp = HyperPars()
hp.rt_prec = 1.0/(across_file_rt_sd*across_file_rt_sd)
hp.rt_prior_prec = 5E-3
hp.alpha = alpha_rt

# turn all_bins into features
features = []
for ab in all_bins:
    f = Feature(ab.bin_id, 0, ab.rt, 0, file_id=ab.origin)
    f.top_id = ab.top_id
    features.append(f)

# construct the possible matrix
data = PeakData(features, None, None, None, None)
data.rt = posterior_bin_rts
data.prior_rts = posterior_bin_rts
data.prior_masses = posterior_bin_masses
N = len(features)
K = len(all_bins)
data.num_clusters = K
data.possible = sp.lil_matrix((N, K), dtype=np.int)
data.matRT = sp.lil_matrix((N, K), dtype=np.float)

# populate possible and matRT
sys.stdout.write("Building matrices for second stage clustering ")
for n in range(N):
    
    if n%200 == 0:
        sys.stdout.write('.')                            

    f = features[n]    
    current_mass, current_rt, current_intensity = f.mass, f.rt, f.intensity
    rt_ok = utils.rt_match(current_rt, np.array(data.prior_rts), across_file_rt_sd*2)
    check = rt_ok
    pos = np.flatnonzero(check)
    for k in pos:
        bb = all_bins[k]
        valid = False
        if f.feature_id == bb.bin_id and f.file_id == bb.origin:
            valid = True
        elif f.top_id == bb.top_id and f.file_id != bb.origin:
            # each bin can only link to those from the same top bin but from different file
            valid = True
        if valid:
            data.possible[n, k] = 1
            data.matRT = current_rt
    # possible_clusters = np.nonzero(data.possible[n, :])[1]
    # assert len(possible_clusters) > 0, str(f) + " has no possible clusters"

    # make the matrices more sparse
    
sys.stdout.write("\n")            

# use variational bayes and a finite mixture model on the RT instead ...
mm = DiscreteVB(data, hp)
mm.n_iterations = 20
mm.run()

# plot distribution of values in ZZ
counter = {}
ZZ = mm.Z.tocsr() * mm.Z.tocsr().transpose()
x = []
cx = ZZ.tocoo()    
for i,j,v in itertools.izip(cx.row, cx.col, cx.data):
    x.append(v)       
    bin1 = all_bins[i]
    bin2 = all_bins[j]
    if bin1.origin != bin2.origin:
        tup = (bin1, bin2)
        counter[tup] = v
x = np.array(x)
plt.figure() 
plt.hist(x, 10)
plt.title("DP RT clustering -- ZZ")
plt.xlabel("Probabilities")
plt.ylabel("Count")
plt.show()        

# Z = mm.Z.tocsc()
# s = Z.sum(0)
# nnz_idx = s.nonzero()[1]  
# nnz_idx = np.squeeze(np.asarray(nnz_idx)) # flatten the thing
# counter = {}
# for k in nnz_idx:
#     col = Z.getcol(k)
#     prod = 1.0
#     indices = col.indices.tolist()
#     values = col.data.tolist()
#     members = []
#     for i in range(len(indices)):
#         if values[i] > 0:
#             index = indices[i]
#             bb = all_bins[index]
#             prod *= values[i]
#             members.append(bb)
#     counter[tuple(members)] = prod

# print report of aligned peaksets in descending order of probabilities
print 
print "=========================================================================="
print "REPORT"
print "=========================================================================="
sorted_list = sorted(counter.items(), key=itemgetter(1), reverse=True)
probs = []
i = 0
for item in sorted_list:
    members = item[0]
    if len(members)==1:
        continue # skip all the singleton stuff
    prob = item[1]
    matched_list = match_features(members)
    for features in matched_list:
        if len(features)==1:
            continue
        mzs = np.array([f.mass for f in features])
        rts = np.array([f.rt for f in features])
        avg_mz = np.mean(mzs)
        avg_rt = np.mean(rts)
        print str(i+1) + ". avg m/z=" + str(avg_mz) + " avg RT=" + str(avg_rt) + " prob=" + str(prob)
        for f in features:
            msg = annotations[f]            
            output = "\tfeature_id {:5d} file_id {:d} mz {:3.5f} RT {:5.2f} intensity {:.4e}\t{:s}".format(
                        f.feature_id, f.file_id, f.mass, f.rt, f.intensity, msg)
            print(output) 
        probs.append(prob)
        i += 1

probs = np.array(probs) 
plt.figure()
plt.hist(probs, 10)
plt.title("Aligned peaksets probabilities")
plt.xlabel("Probabilities")
plt.ylabel("Count")
plt.show()     

end = time.time()
print
utils.timer("TOTAL ELAPSED TIME", start, end)
time.sleep(120)