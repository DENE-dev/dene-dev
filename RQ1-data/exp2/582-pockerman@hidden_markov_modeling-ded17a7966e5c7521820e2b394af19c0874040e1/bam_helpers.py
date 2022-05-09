"""
Utilities for working with bam files
"""
import math
import pysam
import logging
from collections import Counter
from helpers import Window, Observation, DUMMY_ID
from helpers import add_window_observation
from exceptions import FullWindowException
from exceptions import Error

DUMMY_BASE = "*"

def extract_windows(chromosome, ref_filename, test_filename, **args):

    """
    Extract the windows that couple the seq_file and ref_files
    for the given chromosome
    :param chromosome: chromosome name (str)
    :param ref_file: The reference file
    :param test_file: The sequence file
    :return:
    """

    windowcapacity = args["windowsize"]
    start_idx = args["start_idx"]
    end_idx = args["end_idx"]
    quality_theshold = args.get("quality_theshold", None)

    with pysam.FastaFile(ref_filename) as ref_file:

        print("\t Reference file: ", ref_file.filename)

        with pysam.AlignmentFile(test_filename, "rb") as test_file:
            print("\t Test file")
            print("\t", test_file.filename)
            print("\t", test_file.description)

            print("=============================\n")

            try:

                ref_list = ref_file.fetch(chromosome, 0, )

                bam_out, errors, adjusted = bam_strip(chromosome=chromosome,
                                                      file=test_file,
                                                      start=start_idx, stop=end_idx,
                                                      quality_theshold=quality_theshold,
                                                      fastadata=ref_list)

                print("\t Number of erros: ", errors)
                print("\t Number of adjusted: ", adjusted)
                print("\t bam output: ", len(bam_out))

                # get the common bases
                # TODO: explain what are we trying to do here
                common_bases(bamdata=bam_out, fastadata=ref_list)

                # find insertions and deletions
                indel_dict = create_indels_dictionary(chromosome=chromosome,
                                                      samfile=test_file,
                                                      start=start_idx, stop=end_idx)

                # extract the windows
                windows = create_windows(bamlist=bam_out,
                                          indel_dict=indel_dict,
                                          fastdata=ref_list,
                                          windowcapacity=windowcapacity,
                                          start=start_idx,
                                          end=end_idx,
                                          fill_missing_window_data=args.get("fill_missing_window_data", False),
                                          fill_missing_window_data_factor=args.get("fill_missing_window_data_factor",0))

                return windows
            except Exception as e:
                print(str(e))
                raise


def bam_strip(chromosome, file, start, stop, **kwargs):

    """
    get the contents of the file starting at start position and ending
    at stop position for the given chromosome
    """
    errors = 0
    adjusted = 0
    bam_out = []

    # move column-wise
    for pileupcolumn in file.pileup(chromosome, start, stop,
                                        truncate=True, ignore_orphans=False):

            bam_out, adjusted_tmp, errors_tmp = \
                get_query_sequences(pileupcolumn=pileupcolumn,
                                    bam_out=bam_out,
                                    use_indels=True,
                                    do_not_use_indels_on_error=True,
                                    quality_theshold=kwargs.get("quality_theshold", None),
                                    fastadata=kwargs.get("fastadata", None))

            adjusted += adjusted_tmp
            errors += errors_tmp

    return bam_out, errors, adjusted


def create_windows(bamlist, indel_dict, fastdata,
                   windowcapacity, start, end, **kwargs):

    """
    Arrange the given bamlist into windows of size windowcapacity.
    Note that a window is not necessary that will have the
    windowcapacity items. windowcapacity simply indicates the
    maximum number of observations that should be
    added in a window
    :param bamlist:
    :param indel_dict: insertions/deletions directory
    :param fastdata: The reference sequence
    :return: a list of Window instances
    """

    if not bamlist:
        raise Error("No test sequence is provided")

    if not fastdata:
        raise Error("No reference sequence is provided")

    # the returned list of windows
    windows = []

    idstart = 0
    window = Window(idx=idstart, capacity=windowcapacity)
    previous_observation = None

    for idx, item in enumerate(bamlist):

        # create an observation
        observation = Observation(position=item[0],
                                  read_depth=item[1],
                                  base= item[2])

        if previous_observation is not None:

            # is this sequential?
            if int(observation.position) == int(previous_observation.position) + 1:

                # yes it is...nice add it to the window
                # and update the observation
                window = add_window_observation(window=window,
                                                windows=windows,
                                                observation=observation,
                                                windowcapacity=windowcapacity)

                previous_observation = observation
            else:

                # there is a gap we cannot simply
                # add the observation as this may have
                # to be added to the next window depending
                # on the size of the gap.

                # fill in the missing info from the
                # reference file
                window_gaps = _get_missing_gap_info(start=int(previous_observation.position)+1,
                                                    end=int(observation.position)-1,
                                                    fastdata=fastdata)

                # after getting the missing info we try to add it
                # to the window. we may have accumulated so much info that
                # we exceed the window capacity. For example
                # a window already has windowcapacity - 2 items
                # and len(window_gaps) is 10. In this case we need
                # to create a new window

                for win_gap_item in window_gaps:
                    dummy_observation = Observation(position=win_gap_item[0],
                                                    read_depth=win_gap_item[1],
                                                    base= win_gap_item[2])

                    window = add_window_observation(window=window, windows=windows,
                                                    observation=dummy_observation,
                                                    windowcapacity=windowcapacity)

                # add also the current observation
                # that led us here
                window = add_window_observation(window=window, windows=windows,
                                                observation=observation,
                                                windowcapacity=windowcapacity)

                previous_observation = observation
        else:

            # that's the first observation
            window = add_window_observation(window=window, windows=windows,
                                            observation=observation,
                                            windowcapacity=windowcapacity)
            previous_observation = observation

    # catch also the last window. The last
    # window may not be using all its capacity
    # as this depends on the partitioning. Optionally
    # we fill in the missing data if that was requested
    if len(window) != window.capacity():

      # fill in missing data if this is requested
      if kwargs.get("fill_missing_window_data", False):
        while window.has_capacity():
          window.add(observation=Observation(position=DUMMY_ID,
                                  read_depth=kwargs["fill_missing_window_data_factor"],
                                  base= [DUMMY_BASE]))

      windows.append(window)

    return windows


def get_query_sequences(pileupcolumn, bam_out,
                        use_indels=True,
                        do_not_use_indels_on_error=True,
                        **kwargs):

    """
    Given a pysam.PileupColumn instance, it updates the bam_out
    list with the relevant entries corresponding to the given column.
    That is it appends to bam_out the following
    sublist
    [pileupcolumn.reference_pos, pileupcolumn.n, [list of bases mapping to the reference_pos]]

    If an error occurs, the sublist of bases mapping to the reference position is substituted
    with the string "ERROR".
    Client code then should decide how to fill this entry or disregard it altogether

    :param pileupcolumn: the pysam.PileupColumn
    :param bam_out: list of lists. Each sublist has the
                    following structure [pileupcolumn.reference_pos,
                                         pileupcolumn.n,
                                         [list of bases mapping to the reference_pos]]

    :param use_indels: boolean whether indels should be used with the query
    :param do_not_use_indels_on_error: boolean if the query that uses indels fails
                                        and this flag is True allow for a fall over by
                                        performing the same query with use_indels = False

    :return: updated list, number of adjustments, number of errors
    """
    temp = []
    adjusted = 0
    errors = 0

    # add the reference position
    temp.append(pileupcolumn.reference_pos)

    # if the count is zero then we consult the reference
    # at this position if we have a reference file
    if pileupcolumn.n == 0 and "fastadata" in kwargs:

      # when we consult the reference no RD
      temp.append(0)

      # plus 1 since bam is zero-bsed and FASTA is 1 based
      temp.append([kwargs["fastadata"][pileupcolumn.reference_pos + 1]])
    elif pileupcolumn.n == 0:
      # we cannot do anything log the error and return
      logging.error("At position: {0} read \
                    count is zero and cannot use ref file.".format(pileupcolumn.reference_pos))
      return bam_out, 0, 1
    else:
      # we have reads  pileupcolumn.n != 0
      temp.append(pileupcolumn.n)

      # get the read qualities for the column
      quality = pileupcolumn.get_query_qualities()
      quality_threshold = kwargs.get("quality_theshold", None)
      try:
          # append bases only if the quality of the read
          # satisfies our threshold

          query_sequences = pileupcolumn.get_query_sequences(add_indels=use_indels)

          if len(query_sequences) != len(quality):
            logging.error("len(query_sequences) not equal to len(quality). pysam error?")
          else:

            if quality_threshold:
              filtered_bases = [ query_sequences[i] for i, q in enumerate(quality)
                                if q >= quality_threshold]


              temp.append(filtered_bases)
            else:
              temp.append(query_sequences)
            bam_out.append(temp)
      except Exception as e:

          # try a fall out extra step only if it makes sense
          if do_not_use_indels_on_error and use_indels:
              try:

                  query_sequences = pileupcolumn.get_query_sequences(add_indels=False)

                  if len(query_sequences) != len(quality):
                    logging.error("len(query_sequences) not equal to len(quality). pysam error?")
                  else:

                    if quality_threshold:
                       filtered_bases = [ query_sequences[i] for i, q in enumerate(quality)
                                         if q >= quality_threshold]
                       temp.append(filtered_bases)
                    else:
                      temp.append(query_sequences)

                    # flag to show indels not assessed.
                    # TODO: Do we really need that?
                    temp.extend("*")
                    bam_out.append(temp)

                    # once in here we always adjust
                    adjusted += 1
              except:
                  errors += 1
                  logging.error("An error occured at position {0} whilst \
                                reading query sequences.".format(pileupcolumn.reference_pos))
          else:
              errors += 1
              logging.error("An error occured at position {0} whilst \
                            reading query sequences.".format(pileupcolumn.reference_pos))


    return bam_out, adjusted, errors


def create_indels_dictionary(chromosome, samfile, start, stop):
    """
    Insertion/deletions for the given position
    :param chromosome: the region to use
    :param samfile: BAM  file instance
    :param start:
    :param stop:
    :return:
    """

    indels = {}

    for i, pileupcolumn in enumerate(samfile.pileup(chromosome, start, stop,
                                                    truncate=True, ignore_orphans=False)):
        indel_count = 0
        for pileupread in pileupcolumn.pileups:

            # start counting indels when first
            # isertion/deletion  is encountered
            if (pileupread.indel != 0):
                indel_count += 1

            if indel_count > 0:
                indels.update({str(pileupcolumn.pos):
                               (pileupcolumn.get_query_sequences(add_indels=True))})

    return indels


def common_bases(bamdata, fastadata):

    """
    Fill in the information in bamdata by using the
    reference sequence given in fastadata. The bamdata
    is a list containing lists of the form
    # [reference_pos, count_number, [list of bases.  usually a single base]]
    :param bamdata: The bamdata to fill in
    :param fasta: The reference data
    :return:
    """

    for x in bamdata:

        try:
            # the bamdata should be [ref_pos, count, [bases]]
            if x[1] == 1 and len(x) < 3:
                # appending the corresponding base for
                # this position from hg38 ref fasta
                #x.append((fastadata[x[0] + 1]))
                logging.error(" Bam item does not have the correct format")

            else:
                # provides the element which reaches the
                # highest occurrence first.
                common_count = Counter(x[2]).most_common(1)

                # delete from the original bam entry what is present
                # from the entry position 2 and backwards


                try:
                    # when the most common mapped base to the position is an
                    # indel then all elements of the string are appended
                    # to the list (see screenshot on windows staff account).
                  if len(common_count) != 0:
                    if len(common_count[0][0]) > 1:
                      del (x[2:])
                      indel = common_count[0][0]
                      x.extend([indel[0]])
                    else: #len(common_count[0][0]) == 0:

                      del (x[2:])
                      # extend adds the new elements into the list,
                      # not into the list as a separate list.
                      x.extend([common_count[0][0]])
                  else:
                      logging.warning(" No common bases found don't know what to do")
                      logging.warning(" x looked at is {0}".format(x))

                except Exception as e:
                   print("Common count is: {0}".format(common_count))
                   print("x is: {0}" .format(x))
                   raise
        except Exception as e:
            raise Error("An error occurred whilst extracting\
                        common_bases {0}".format(str(e)))


def _get_insertions_and_deletions_from_indel(indel, insertions, deletions):

    """
    For every base in the given indel check whether it contains
    "+" or "-". If yes append this  to the appropriate array
    :param indel:
    :param insertions: list representing insertions
    :param deletions: list representing deletions
    :return:
    """

    for base in indel:
        if "+" in base:
            insertions.append(base)
        if "-" in base:
            # for each element that contains one or more indels, the value (list of bases)
            # is iterated, deletions are represented in the read with a "+" in pysam, whilst
            # insertions are represented with a "-". Any indels that map to the position
            # are appended to deletions e.g. [T+2N] and insertions lists e.g. [A-3GTT]
            deletions.append(base)


def _uniquefy_insertions_and_deletions(insertions, deletions):

    insertions_set = set(insertions)
    deletions_set = set(deletions)

    # grab the third character in the string, which is he number of inserted/deleted bases.
    unique_insertions = [int(x[2]) for x in insertions_set]
    unique_deletions = [int(x[2]) for x in deletions_set]
    return unique_insertions, unique_deletions


def _get_insertion_deletion_difference(unique_insertions, unique_deletions):
        """
        Returns the absolute difference
        between the two given lists
        :param unique_insertions:
        :param unique_deletions:
        :return:
        """
        sum_unique_insert = sum(unique_insertions)
        sum_unique_delete = sum(unique_deletions)
        net_indel = math.fabs(sum_unique_delete - sum_unique_insert)
        return net_indel


def _get_missing_gap_info(start, end, fastdata):

    fastdata_range = fastdata[start:end]

    # the position of the skipped element.
    skipped_pos = start
    window_gaps = []

    for base in fastdata_range:

        skipped_temp = []
        skipped_temp.append(skipped_pos)

        # 0 to represent the read depth for this position.
        skipped_temp.append(0)
        skipped_temp.append(base)
        window_gaps.append(skipped_temp)

    return window_gaps