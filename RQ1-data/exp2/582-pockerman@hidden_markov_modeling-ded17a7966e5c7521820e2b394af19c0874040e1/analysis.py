import argparse
import logging
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pomegranate import*

from helpers import read_configuration_file
from helpers import set_up_logger
from helpers import save_hmm
from helpers import flat_windows_from_state
from helpers import HMMCallback
from helpers import print_logs_callback

from bam_helpers import extract_windows
from cluster import Cluster
from hypothesis_testing import SignificanceTestLabeler
from preprocess_utils import fit_distribution
from preprocess_utils import build_clusterer
from exceptions import Error


def create_clusters(windows, configuration):

  kwargs = {"clusterer":{ "name":configuration["clusterer"],
                          "config":configuration["clusterer"]["config"]}}


  clusterer =  build_clusterer(data=windows,
                               nclusters=len(configuration["states"]),
                               method="kmedoids",
                               **kwargs)

  clusters_indexes = clusterer.get_clusters()
  clusters = []

  for i in range(len(clusters_indexes)):
    clusters.append(Cluster(id_ = i, indexes=clusters_indexes[i]))

  labeler = SignificanceTestLabeler(clusters=clusters,
                                    windows=windows)

  labeled_clusters = labeler.label(test_config=configuration["labeler"])

  # update windows states
  for state in labeled_clusters:
    cluster = labeled_clusters[state]
    indexes = cluster.indexes

    for idx in indexes:
      windows[idx].set_state(cluster.state)

  return labeled_clusters

def init_hmm(clusters, windows, configuration):

  # create the HMM
  hmm_model = HiddenMarkovModel(name=configuration["HMM"]["name"],
                                start=None, end=None)


  state_to_dist = {}
  states = []
  for cluster in clusters:
    state_to_dist[cluster.state.name] = \
    fit_distribution(data=cluster.get_data_from_windows(windows=windows),
                     dist_name=configuration["fit_states_dist"][cluster.state.name])
    states.append(State(state_to_dist[cluster.state.name], name=cluster.state.name))


  # add the states to the model
  hmm_model.add_states(states)

  # construct the transition matrix.
  # We create a dense HMM with equal
  # transition probabilities between each state
  # this will be used for initialization when
  # we fit the model. All states have an equal
  # probability to be the starting state or we could

  for i, cluster in enumerate(clusters):
    hmm_model.add_transition(hmm_model.start,
                             states[i],
                              configuration["HMM"]["start_prob"][cluster.state.name])

  for i in states:
    for j in states:

      if i == j:
        hmm_model.add_transition(i, j, 0.95)
      else:
        hmm_model.add_transition(i, j, 0.05)

  # finally we need to bake
  hmm_model.bake(verbose=True)
  return hmm_model

def hmm_train(clusters, windows, configuration):

  print("\tStart HMM training....")

  # initialize the model
  hmm_model = init_hmm(clusters=clusters,
                       windows=windows,
                       configuration=configuration)


  flatwindows = flat_windows_from_state(windows=windows,
                                        configuration=configuration,
                                        as_on_seq=False)

  #flatwindows = flat_windows(windows=windows)

  #print("Flatwindows are: ", flatwindows)

  #flatwindows = flat_windows(windows)
  print("Start training HMM")

  # fit the model
  hmm_model, history = hmm_model.fit(sequences=[flatwindows],
                                           #min_iterations=,
                                           algorithm=configuration["HMM"]["train_solver"],
                                           return_history=True,
                                           verbose=True,
                                           lr_decay=0.6,
                                           callbacks=[HMMCallback(callback=print_logs_callback)],
                                           inertia=0.01)

  print("Done training HMM")
  hmm_model.bake()

  p_d_given_m = hmm_model.log_probability(sequence=flatwindows)
  print("P(D|M): ", p_d_given_m)
  print(hmm_model.predict_proba(flatwindows))
  viterbi_path=hmm_model.viterbi(flatwindows)
  trans, ems = hmm_model.forward_backward( flatwindows )
  print(trans)

  # plot the model
  #plt.figure( figsize=(10,6) )
  #hmm_model.plot()
  #plt.show()


  save_hmm(hmm_model=hmm_model,
                   configuration=configuration,
                   win_interval_length=0)


def make_windows(configuration):

    wga_start_idx = configuration["test_file"]["start_idx"]
    wga_end_idx = configuration["test_file"]["end_idx"]

    if wga_end_idx == "none":
      wga_end_idx = None
    else:
      wga_end_idx = int(wga_end_idx)

    windowsize = configuration["window_size"]
    chromosome = configuration["chromosome"]

    print("\t\tStart index used: ", wga_start_idx)
    print("\t\tEnd index used: ", wga_end_idx)
    print("\t\tWindow size: ", windowsize)
    print("\t\tChromosome: ", chromosome)

    args = {"start_idx": int(wga_start_idx),
            "end_idx": wga_end_idx,
            "windowsize": int(windowsize)}

    try:

        # TODO: Extractig initial windows is independent
        # we can do so in parallel

        # extract the windows for the WGA treated file
        wga_windows = extract_windows(chromosome=chromosome,
                                      ref_filename=configuration["reference_file"]["filename"],
                                      test_filename=configuration["test_file"]["filename"],
                                      **args)

        if len(wga_windows) == 0:
            raise Error("WGA windows have not been created")
        else:
            print("\t\tNumber of windows: ", len(wga_windows))


        non_wga_start_idx = configuration["no_wga_file"]["start_idx"]
        non_wga_end_idx = configuration["no_wga_file"]["end_idx"]

        args = {"start_idx": int(non_wga_start_idx),
                "end_idx": (non_wga_end_idx),
                "windowsize": int(windowsize)}

        # exrtact the non-wga windows
        non_wga_windows = extract_windows(chromosome=chromosome,
                                          ref_filename=configuration["reference_file"]["name"],
                                          test_filename=configuration["no_wga_file"]["filename"], **args)

        if len(non_wga_windows) == 0:
            raise Error("Non-WGA windows have not  been created")
        else:
            print("\t\tNumber of windows: ", len(wga_windows))

        return wga_windows, non_wga_windows

    except KeyError as e:
        logging.error("Key: {0} does not exit".format(str(e)))
    except Error as e:
        logging.error(str(e))
    except Exception as e:
        logging.error("Unknown exception occured: " + str(e))




def main():

    print("Starting analysis")
    description = "Check the README file for information on how to use the script"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--config', type=str, default='config.json',
                        help='You must specify a json formatted configuration file')
    args = parser.parse_args()

    config_file = args.config
    configuration = read_configuration_file(config_file)

    # configure the logger to use
    set_up_logger(configuration=configuration)
    logging.info("Checking if logger is sane...")

    wga_windows, non_wga_windows = make_windows(configuration=configuration)

    print("Extracted dataset....")
    print("Start clustering....")
    # create clusters
    wga_clusters, _ = create_clusters(windows=wga_windows,
                                      configuration=configuration)

    print("Number of wga_clusters used: {0}".format(len(wga_clusters)))

    for cluster in wga_clusters:
      print("State modelled by cluster {0} is {1}".format(wga_clusters[cluster].cidx,
                                                          wga_clusters[cluster].state.name))

    hmm_train(clusters=wga_clusters.values(),
              windows=wga_windows,
              configuration=configuration)

    print("Finished analysis")


if __name__ == '__main__':
    main()