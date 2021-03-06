# This file contains a wrapper class that represents word trained embeddings
from gensim.models import KeyedVectors
from mma_word_embeddings.utils import normalize_vector, make_pairs, kl_divergence, mmd2
import numpy as np
from itertools import combinations_with_replacement, combinations, product
import pandas as pd
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from sklearn.manifold import TSNE
from collections import Counter
from random import sample
import glob
import seaborn as sns
import networkx as nx
import matplotlib.cm as cm


# Make pandas print full data frame
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
pd.options.display.float_format = '{:,.4f}'.format

COLORMAP = mcolors.LinearSegmentedColormap.from_list("MyCmapName", ["r", "w", "g"])


class EmbeddingError(Exception):
    """Exception raised by a Model object when something is wrong.
    """


class WordEmbedding:
    """Representation of a word embedding, which is a map from word strings to vectors."""

    def __init__(self, path_to_embedding, path_training_data=None):

        print("Loading embedding {} ... ".format(path_to_embedding))

        try:
            # load the word vectors of an embedding
            self._word_vectors = KeyedVectors.load(path_to_embedding)
        except:
            raise EmbeddingError("Failed to load the embedding. In 99.999% of all cases this means your "
                                 "path is wrong. Good luck.")

        self.description = "This object represents the {} word embedding.".format(path_to_embedding)
        self.path_to_embedding = path_to_embedding.replace("/content/drive/My Drive/", "")

        self.training_data = None
        if path_training_data is not None:
            self.load_training_data(path_training_data)

        print("...finished loading.")

    def __str__(self):
        return "<Embedding {}>".format(self.path_to_embedding)

    def vocab(self, n_grams=None):
        """Return the vocabulary in the embedding."""

        if n_grams is not None:
            if n_grams not in range(1, 100):
                raise ValueError("n_grams arguemnt must be between 1 and 100. ")

            voc = []
            for word in self.vocab():
                if word.count("_") == n_grams - 1:
                    voc.append(word)
        else:
            voc = list(self._word_vectors.vocab)

        return sorted(voc)

    def vocab_size(self):
        """Return the size of the vocabulary in the embedding."""

        return len(list(self._word_vectors.vocab))

    def in_vocab(self, word):
        """Return whether word is in vocab."""
        return word in list(self._word_vectors.vocab)

    def random_words(self, n_words=100, min_frequency=None):
        """Return a list of random words from the vocab of this embedding.

        If the training data is loaded, the minimum frequency can be specified.

        Args:
            n_words (int): number of random words to select
            min_frequency (int): minimum frequency of the word in the training data

        Returns:
            list(str): random words
        """

        if min_frequency is not None and self.training_data is None:
            raise ValueError("This function needs access to the training data. "
                             "Please load the training data with the 'load_training_data()' "
                             "function and then try again. ")

        if min_frequency is not None:
            vocab = self.vocab_sorted_by_frequency_in_training_data(more_frequent_than=min_frequency)
            vocab = vocab['Word'].tolist()
        else:
            vocab = self.vocab()

        return sample(vocab, n_words)

    def load_training_data(self, path_training_data):
        """Load training data into embedding after embedding was created."""
        training_data = []
        if path_training_data is not None:
            with open(path_training_data, "r") as f:
                for line in f:
                    stripped_line = line.strip()
                    line_list = stripped_line.split()
                    training_data.append(line_list)
            self.training_data = training_data

    def context_in_training_data(self, word, n=3):
        """Return whether word is in vocab. Only works if training data was loaded.
        Args:
            word (str): Word to search for
            n (int): number of neighbouring words to print
        """
        if self.training_data is None:
            raise ValueError("This function needs access to the training data. "
                             "Please load the training data with the 'load_training_data()' "
                             "function and then try again. ")
        context = []
        for sentence in self.training_data:
            for idx, token in enumerate(sentence):
                if word == token:
                    start = 0 if (idx - n < 0) else idx - n
                    stop = len(sentence)-1 if (idx + n > len(sentence)-1) else idx + n
                    string = " ".join(sentence[start:stop+1])
                    context.append(string)
        return context

    def frequency_in_training_data(self, word):
        """Return how often the word appears in the training data. Only works if training data was loaded."""
        if self.training_data is None:
            raise ValueError("This function needs access to the training data. "
                             "Please load the training data with the 'load_training_data()' "
                             "function and then try again. ")

        counter = 0
        for document in self.training_data:
            for wrd in document:
                if wrd == word:
                    counter += 1

        return counter

    def sort_by_frequency_in_training_data(self, list_of_words):
        """Return a table in which the words are sorted by the frequency with which they appear in the training data."""
        freqs = [self.frequency_in_training_data(word) for word in list_of_words]
        res = pd.DataFrame({'Word': list_of_words, 'Frequency': freqs})
        res = res.sort_values(by='Frequency', axis=0, ascending=False)
        res = res.reset_index(drop=True)
        return res

    def vocab_sorted_by_frequency_in_training_data(self, first_n=None, more_frequent_than=None):
        """Return the vocab sorted by the frequency with which they appear in the training data.

        Args:
             first_n (int): only return n most frequent words (-n for last n words). Overwrites up_to argument!
             more_frequent_than (int): only return words up to frequency "up_to"
        """

        if self.training_data is None:
            raise ValueError("This function needs access to the training data. "
                             "Please load the training data with the 'load_training_data()' "
                             "function and then try again. ")

        if more_frequent_than == 0:
            more_frequent_than = None

        flat_training_data = [wrd for document in self.training_data for wrd in document]
        c = Counter(flat_training_data)

        res = pd.DataFrame({"Word": c.keys(), "Frequency": c.values()})
        if first_n is not None:
            res = res.head(n=first_n)
        if more_frequent_than is not None:
            res = res[res['Frequency'] > more_frequent_than]
        return res

    def training_data_size(self):
        """Return how many words are in the training data. Only works if training data was loaded."""
        if self.training_data is None:
            raise ValueError("This function needs access to the training data. "
                             "Please load the training data with the 'load_training_data()' "
                             "function and then try again. ")

        counter = 0
        for sentence in self.training_data:
            counter += len(sentence)
        return counter

    def vocab_containing(self, word_part, show_frequency=False):
        """Return all words in the vocab that contain the word_part as a substring.

        Args:
            word_part (str): sequence of letters like "afro" or "whit"
            show_frequency (bool): if True, also show frequencies
        If the training data is loaded, this function will show frequencies as well.
        """
        if show_frequency:
            if self.training_data is None:
                raise ValueError("This function needs access to the training data. "
                                 "Please load the training data with the 'load_training_data()' "
                                 "function and then try again. ")

            subset = [[w, self.frequency_in_training_data(w)] for w in sorted(list(self._word_vectors.vocab)) if word_part in w]
            subset = pd.DataFrame(subset, columns=["Word", "Frequency"])
            subset = subset.sort_values(by='Frequency', axis=0, ascending=False)
        else:
            subset = [w for w in sorted(list(self._word_vectors.vocab)) if word_part in w]
        return subset

    def vector(self, word):
        """Return the normalized vector representation of 'word' in the embedding."""

        return normalize_vector(self._word_vectors[word])

    def vectors(self, list_of_words):
        """Return a list of the normalized vector representations of each 'word' in 'list_of_words'."""
        return [self.vector(word) for word in list_of_words]

    def difference_vector(self, word1, word2, normalize=False):
        """Return the difference vector of 'word1' and 'word2'.
        Args:
            word1 (str): first word
            word2 (str): second word
            normalize: whether the difference should be normalised

        Returns:
            ndarray: normalised difference vector
            """

        vec1 = self.vector(word1)
        vec2 = self.vector(word2)
        if np.allclose(vec1, vec2, atol=1e-10):
            raise ValueError("The two words have the same vector representation, cannot compute their difference.")
        diff = vec1 - vec2

        if normalize:
            diff = normalize_vector(diff)
        return diff

    def difference_vectors(self, list_of_word_pairs, normalize=False):
        """Return a list of difference vectors for the word pairs provided."""
        return [self.difference_vector(word1, word2, normalize=normalize) for word1, word2 in list_of_word_pairs]

    def centroid_of_difference_vectors(self, list_of_word_pairs, normalize_diffs=False, normalize_centroid=False):
        """Return the centroid vector of the differences of the word pairs provided."""

        difference_vecs = self.difference_vectors(list_of_word_pairs, normalize=normalize_diffs)
        centroid = np.mean(np.array(difference_vecs), axis=0)
        if normalize_centroid:
            return normalize_vector(centroid)
        return centroid

    def centroid_of_vectors(self, list_of_words, normalize=False):
        """Return the centroid vector of the words provided."""

        vecs = [self.vector(word) for word in list_of_words]
        vecs = np.array(vecs)
        centroid = np.mean(vecs, axis=0)
        if normalize:
            return normalize_vector(centroid)
        return centroid

    def principal_components(self, list_of_words=None, n_components=3, normalize=False):
        """Get the n_component first principal component vectors of the words.

        Args:
            list_of_words (list[str]): list of words
            n_components (int): number of components
        Returns:
            list of arrays
        """

        X = [self.vector(word) for word in list_of_words]
        X = np.array(X)
        pca_transformer = PCA(n_components=n_components)
        pca_transformer.fit_transform(X)

        principal_vectors = pca_transformer.components_[:n_components]
        if normalize:
            principal_vectors = [normalize_vector(vec) for vec in principal_vectors]
        return principal_vectors

    def principal_components_variance(self, list_of_words=None, n_components=3):
        """The amount of variance explained by each of the principal components of the words in the list.

        Args:
            list_of_words (list[str]): list of words
            n_components (int): number of components
        Returns:
            list
        """

        X = [self.vector(word) for word in list_of_words]
        X = np.array(X)
        pca_transformer = PCA(n_components=n_components)
        pca_transformer.fit_transform(X)

        explained_variance = pca_transformer.explained_variance_[:n_components]
        return explained_variance

    def similarity(self, word1, word2):
        """Return the similarity between 'word1' and 'word2'. The result is a value between -1 and 1."""
        return np.dot(self.vector(word1), self.vector(word2))

    def similarities(self, list_of_word_pairs):
        """Return the cosine similarities between words in list of word pairs."""
        result = [[word1, word2, round(self.similarity(word1, word2), 3)] for word1, word2 in list_of_word_pairs]
        result_dataframe = pd.DataFrame(result, columns=['Word1', 'Word2', 'Similarity'])
        result_dataframe = result_dataframe.sort_values(["Similarity"], axis=0)
        return result_dataframe

    def most_similar(self, word, n=10):
        """Return the words most similar to 'word'."""

        ms = self._word_vectors.most_similar(word, topn=n)
        ms = [(word, round(s, 3)) for word, s in ms]
        return ms

    def most_similar_by_vector(self, vector, n=10):
        """Return the words most similar to 'vector'."""

        return self._word_vectors.similar_by_vector(vector, topn=n)

    def least_similar(self, word, n=10):
        """Return the words least similar to 'word'."""
        most_sim = self._word_vectors.most_similar(word, topn=self.vocab_size())
        last_n = most_sim[-n:]
        return last_n[::-1]

    def least_similar_by_vector(self, vector, n=10):
        """Return the words least similar to 'word'."""
        return self.most_similar_by_vector(-vector, n=n)

    def similarities_of_differences(self, list_of_word_pairs):
        """Construct the difference vectors for each word pair and return a dictionary of their similarities."""

        # make all unique combinations of pairs
        combinations_all_pairs = combinations_with_replacement(list_of_word_pairs, 2)
        # remove doubles - somehow the usual '==' does not work in colab
        combinations_all_pairs = [c for c in combinations_all_pairs if c[0][0] != c[1][0] or c[0][1] != c[1][1]]

        result = []
        for combination in list(combinations_all_pairs):
            pair1 = combination[0]
            pair2 = combination[1]

            # compute difference vectors
            diff_pair1 = self.vector(pair1[0]) - self.vector(pair1[1])
            diff_pair2 = self.vector(pair2[0]) - self.vector(pair2[1])

            # normalise differences
            diff_pair1 = normalize_vector(diff_pair1)
            diff_pair2 = normalize_vector(diff_pair2)

            sim = np.dot(diff_pair1, diff_pair2)
            sim = round(sim, 4)

            # save in nice format
            entry1 = pair1[0] + " - " + pair1[1]
            entry2 = pair2[0] + " - " + pair2[1]
            result.append([entry1, entry2, sim])

        result_dataframe = pd.DataFrame(result, columns=['Pair1', 'Pair2', 'Alignment'])
        return result_dataframe

    def words_closest_to_principal_components(self, list_of_words=None, n_components=3, n=5):
        """Get the words closest to the principal components of the word vectors in the vocab.

        Args:
            n_components (int): number of components
            n (int): number of neighbours to print for each component

        Returns:
            DataFrame
        """

        if list_of_words is None:
            list_of_words = self.vocab()

        principal_vecs = self.principal_components(list_of_words, n_components=n_components, normalize=True)

        data = {}

        for idx, vec in enumerate(principal_vecs):
            data['princ_comp' + str(idx+1)] = self.most_similar([vec], n=n)

        df = pd.DataFrame(data)
        return df

    def analogy(self, positive_list, negative_list, n=10):
        """Returns words close to positive words and far away from negative words, as
        proposed in https://www.aclweb.org/anthology/W14-1618.pdf"""
        return self._word_vectors.most_similar(positive=positive_list, negative=negative_list, topn=n)

    def projection(self, test_word, word_pair):
        """Compute the projection of a word to the normalized difference vector of the word pair.

        Read the output as follows: if result is negative, it is closer to the SECOND word, else to the FIRST.

        Args:
            test_word (str): test word
            word_pair (List[str]): list of (two) words defining the dimension

        Returns:
            float in [-1, 1]
        """
        diff = self.difference_vector(word_pair[0], word_pair[1], normalize=True)
        vec = self.vector(test_word)
        projection = np.dot(diff, vec)
        return projection

    def projections(self, test_words, word_pairs):
        """Compute projections of a word to difference vectors ("dimensions") spanned by multiple
        word pairs. Return result as a dataframe.

        Args:
            word (str): test word
            list_of_word_pairs (List[List[str]]): list of word pairs defining the dimension

        Returns:
            DataFrame
        """
        result = []
        for word in test_words:
            for word_pair in word_pairs:
                projection = self.projection(word, word_pair)
                result.append([word, word_pair[0] + " - " + word_pair[1], projection])

        result_dataframe = pd.DataFrame(result, columns=['test', 'dimension', 'projection'])
        if self.training_data is not None:
            result_dataframe['test_freq'] = [self.frequency_in_training_data(word) for word in result_dataframe['test']]
        return result_dataframe

    def projections_to_bipolar_dimensions(self, test, dimensions, normalize_before=False, normalize_centroids=True):
        """ Compute the projections of test words onto bipolar dimensions. Each bipolar dimension is constructed from
        two clusters of words.

        The dimension is constructed as difference of the two (unnormalised) centroids of the words in the clusters.

        Note that up to a constant which is independent of the test word, this is the same as

        * Computing the difference between the averages of the projections of a test word to words in
          the two clusters.

        * Computing the average of projections onto the difference between word pairs formed from the cluster.

        * Computing the projection onto the centroid of differences between word pairs formed from the cluster.

         Args:
            test (str or list[str]): test word like 'land' OR list of test
              words like ['land', 'nurse',...]
            dimensions (dict): dictionary of lists of two clusters like

                    {'gender (male-female)': [['man', 'he',...], ['girl', 'her',...]],
                     'race (black-white)': [['black', ...], ['white', ...]],
                     ...
                     }
        Returns:
            DataFrame
        """
        if isinstance(test, str):
            test_words = [test]
        else:
            test_words = test

        data = []
        for test_word in test_words:

            test_vec = self.vector(test_word)
            row = [test_word]

            for dim_clusters in dimensions.values():

                if len(dim_clusters) != 2:
                    raise ValueError("Generating words must be a list of exactly two lists that contain words.")

                centroid_left_cluster = self.centroid_of_vectors(dim_clusters[0])
                centroid_right_cluster = self.centroid_of_vectors(dim_clusters[1])
                
                if normalize_centroids:
                    centroid_left_cluster = centroid_left_cluster/np.linalg.norm(centroid_left_cluster)
                    centroid_right_cluster = centroid_right_cluster/np.linalg.norm(centroid_right_cluster)
                    
                diff = centroid_left_cluster - centroid_right_cluster
                if normalize_before:
                    diff = normalize_vector(diff)
                res = np.dot(test_vec, diff)
                row.append(res)

            data.append(row)

        cols = ["test_word"] + list(dimensions)

        df = pd.DataFrame(data, columns=cols)
        df = df.sort_values(cols[1:], axis=0, ascending=False)
        return df

    def projections_to_unipolar_dimensions(self, test, dimensions, normalize_before=True):
        """Compute the projection of a test word onto unipolar dimensions.

           The unipolar dimension is the centroid of a cluster of words.

        Args:
            test (str or list[str]): test word like 'land' OR list of test
                                        words like ['land', 'nurse',...]
            dimensions (dict): dictionary of clusters like

                    {'male': ['man', 'he',...]
                     'female': ['him', 'her' ...],
                     ...
                     }
        Returns:
            DataFrame
        """
        if isinstance(test, str):
            test_words = [test]
        else:
            test_words = test

        data = []
        for test_word in test_words:

            test_vec = self.vector(test_word)
            row = [test_word]

            for dim_cluster in dimensions.values():

                if len(np.array(dim_cluster).shape) != 1:
                    raise ValueError("Generating words must be a list of words.")

                centroid = self.centroid_of_vectors(dim_cluster)
                if normalize_before:
                    centroid = normalize_vector(centroid)
                res = np.dot(test_vec, centroid)
                row.append(res)

            data.append(row)

        cols = ["test_word"] + list(dimensions)

        df = pd.DataFrame(data, columns=cols)
        df = df.sort_values(cols[1:], axis=0, ascending=False)
        return df

    def projections_to_principal_components(self, test, dimensions, n_components=3, n=5):
        """Compute the projection of a test word onto the first n_components principal vectors.

        The n words closest to those principal vectors are printed to get a feeling for what these components mean.

        Args:
            test (str or list[str]): test word like 'land' OR list of test
                                        words like ['land', 'nurse',...]
            dimensions (dict): dictionary of clusters like

                    {'male': ['man', 'he',...]
                     'female': ['him', 'her' ...],
                     ...
                     }
            n_components (int): number of components to consider
            n (int): number of similar words to print

        Returns:
            DataFrame
        """
        if isinstance(test, str):
            test_words = [test]
        else:
            test_words = test

        # collect principal vectors
        principal_vecs = {}
        cols = ["test_word"]
        for dim_name, dim_cluster in dimensions.items():

            if len(np.array(dim_cluster).shape) != 1:
                raise ValueError("Generating words must be a list of words.")

            p_vecs = self.principal_components(dim_cluster, n_components=n_components, normalize=True)
            principal_vecs[dim_name] = p_vecs

            for idx, vec in enumerate(p_vecs):
                cols += ["{}-P{}".format(dim_name, idx+1)]
                print("{}-P{} is similar to: ".format(dim_name, idx), self.most_similar([vec], n=n))

        data = []
        for test_word in test_words:

            test_vec = self.vector(test_word)
            row = [test_word]
            for dim_name, p_vecs in principal_vecs.items():

                for vec in p_vecs:
                    res = np.dot(test_vec, vec)
                    row.append(res)

            data.append(row)

        df = pd.DataFrame(data, columns=cols)
        df = df.sort_values(cols[1:], axis=0, ascending=False)
        return df

    def cluster_diversity(self, list_of_words, method="centroid_length", **kwargs):
        """Compute a measure of the diversity of a list of words.

        This is done by computing the distribution of similarities between all possible pairs of words in the cluster,
        and comparing it with a uniform distribution.
        """
        if method == "centroid_length":
            centroid = self.centroid_of_vectors(list_of_words, normalize=False)
            return np.dot(centroid, centroid)

        elif method == "mmd":
            kernel = kwargs.get("kernel", None)

        else:
            raise ValueError("Method {} not recognised.".format(method))

    def plot_diversity(self, list_of_words, bandwidth=0.1):
        """Plot density of the mutual similarities of all words. """
        similarities = []
        for word1, word2 in combinations(list_of_words, 2):
            similarities.append(self.similarity(word1, word2))

        sns.kdeplot(np.array(similarities), bw_method=bandwidth)
        plt.xlim(-1, 1)

    def plot_distance_graph(self, list_of_words, nonlinear=False, scaling=2, padding=1.2):
        """Plot a network where edge length shows the similarity between words"""
        if nonlinear:
            covariance_list = [np.tanh(scaling*self.similarity(word1, word2)) for word1, word2 in product(list_of_words, repeat=2)]
        else:
            covariance_list = [self.similarity(word1, word2) for word1, word2 in product(list_of_words, repeat=2)]
        covariance = np.array(covariance_list).reshape(len(list_of_words), len(list_of_words))
        graph = nx.from_numpy_array(covariance)
        mapping = {i: word for i, word in enumerate(list_of_words)}
        graph = nx.relabel_nodes(graph, mapping)
        pos = nx.spring_layout(graph, scale=0.2)
        nx.draw_networkx_nodes(graph, pos,node_size=15, node_color='lightgray')
        nx.draw_networkx_edges(graph, pos,  edge_color='lightgray')
        y_off = 0.01
        nx.draw_networkx_labels(graph, pos={k: ([v[0], v[1] + y_off]) for k, v in pos.items()})
        xmax = padding * max(xx for xx, yy in pos.values())
        ymax = padding * max(yy for xx, yy in pos.values())
        xmin = padding * min(xx for xx, yy in pos.values())
        ymin = padding * min(yy for xx, yy in pos.values())
        plt.xlim(xmin, xmax)
        plt.ylim(ymin, ymax)
        plt.box(False)
        plt.tight_layout()

    def plot_distance_matrix(self, list_of_words, size=5, nonlinear=False, scaling=2, normalize=False, min=-1):
        """Plot a matrix where each value shows the similarity between words"""
        if nonlinear:
            covariance_list = [np.tanh(scaling*self.similarity(word1, word2)) for word1, word2 in product(list_of_words, repeat=2)]
        else:
            covariance_list = [self.similarity(word1, word2) for word1, word2 in product(list_of_words, repeat=2)]

        covariance = np.array(covariance_list).reshape(len(list_of_words), len(list_of_words))

        plt.figure(figsize=(size, size))
        if normalize:
            plt.imshow(covariance, aspect='equal', cmap='BrBG', vmin=min(covariance_list), vmax=max(covariance_list))
        else:
            plt.imshow(covariance, aspect='equal', cmap='BrBG', vmin=min, vmax=1)

        plt.yticks(ticks=range(len(list_of_words)), labels=list_of_words)
        plt.xticks(ticks=range(len(list_of_words)), labels=list_of_words, rotation=90)
        plt.colorbar()
        plt.tight_layout()


    def plot_pca(self, list_of_words, n_comp=2):
        """Plot the words in list_of_words in a PCA plot.

        Args:
            list_of_words (List[str]): list of words
            n_comp (int): number of principal components
        """
        X = np.array([self.vector(word) for word in list_of_words])
        pca_transformer = PCA(n_components=n_comp)
        pca = pca_transformer.fit_transform(X)

        plt.figure()
        plt.scatter(pca[:, 0], pca[:, 1])
        # Adding annotations
        for i, word in enumerate(list_of_words):
            plt.annotate(' ' + word, xy=(pca[i, 0], pca[i, 1]))

        plt.show()

    def plot_tsne(self, list_of_words, tsne_ncomp=2, pep=15):
        """Plot the words in list_of_words in a PCA plot.

        Args:
            list_of_words (List[str]): list of words
            n_comp (int): number of principal components
        """

        X = np.array([self.vector(word) for word in list_of_words])
        tsne = TSNE(n_components=tsne_ncomp, random_state=0, perplexity=pep).fit_transform(X)

        plt.figure()
        plt.scatter(tsne[:, 0], tsne[:, 1])
        # Adding annotations
        for i, word in enumerate(list_of_words):
            plt.annotate(' ' + word, xy=(tsne[i, 0], tsne[i, 1]))

        plt.show()

    def plot_words_as_colourarray(self, list_of_words, include_centroid=False, include_princ_comp=None,
                                  include_diff_vectors=None):
        """Visualise word vectors as arrays of coloured blocks.

        Args:
            include_centroid (bool): also plot their centroid vector
            include_princ_comp (int): also plot principal comp vecs
            include_diff_vectors (bool): also plot difference vecs
        """
        list_of_words = list_of_words.copy()

        vecs = [self.vector(word) for word in list_of_words]

        extra_vecs = []
        extra_words = []
        if include_centroid:
            extra_vecs.append(self.centroid_of_vectors(list_of_words))
            extra_words.append('centroid')
        if include_princ_comp is not None:
            if not isinstance(include_princ_comp, int):
                raise ValueError("invclude_princ_comp must be an integer like 1, 2, 3...")
            extra_vecs.extend(self.principal_component_vectors(list_of_words))
            for i in range(include_princ_comp):
                extra_words.append('princ_comp' + str(i))
        if include_diff_vectors is not None:
            diff_pairs = make_pairs(list_of_words, list_of_words, exclude_doubles=True)
            extra_vecs.extend(self.difference_vectors(diff_pairs))
            extra_words.extend([word1 + "-" + word2 for word1, word2 in diff_pairs])

        vecs.extend(extra_vecs)
        list_of_words.extend(extra_words)

        X = np.array(vecs)
        plt.figure(figsize=(20, 1 + 0.2 * len(list_of_words)))
        plt.imshow(X)
        plt.yticks(ticks=range(len(list_of_words)), labels=list_of_words)
        plt.xlabel("dimension in embedding space")
        plt.show()


class EmbeddingEnsemble:
    """Applies actions to an list_of_embeddings of trained embeddings."""

    def __init__(self, path_to_embeddings):

        self.list_of_embeddings = []

        if isinstance(path_to_embeddings, list):

            paths = path_to_embeddings

        else:

            paths = glob.glob(path_to_embeddings + '*.emb')

            if len(paths) == 0:
                raise EmbeddingError("Failed to find any appropriate file. Please make sure that "
                                     "there are trained embeddings under this path.".format(path_to_embeddings))

        # Iterate through all paths
        for path in paths:

            try:
                # load the word vectors of an embedding
                emb = WordEmbedding(path)
            except FileNotFoundError:
                raise EmbeddingError("Failed to load the trained embeddings {}. Please make sure that "
                                     "the path to this file really exists.".format(path))

            self.list_of_embeddings.append(emb)

        self.description = "This object represents the list_of_embeddings {} of {} word trained embeddings."\
            .format(path_to_embeddings, len(self.list_of_embeddings))

    def shared_vocab(self):
        """Return the subset of the vocab that is shared by all embeddings in the list_of_embeddings
        (i.e. the intersection of their vocab)."""
        vocabs = [emb.vocab() for emb in self.list_of_embeddings]
        shared_vocab = set(vocabs[0]).intersection(*vocabs)
        return list(shared_vocab)

    def in_vocab(self, word):
        """Return whether word is in vocab."""
        individual = [emb.in_vocab(word) for emb in self.list_of_embeddings]
        data = [['in_vocab'] + individual]
        df = pd.DataFrame(data, columns=[''] + self.cols)
        df['MEAN'] = df.mean(numeric_only=True, axis=1)
        return df

    def similarity(self, word1, word2):
        """Return the cosine similarities between 'word1' and 'word2'."""
        individual = [emb.similarity(word1, word2) for emb in self.list_of_embeddings]
        data = [['similarity'] + individual]
        df = pd.DataFrame(data, columns=[''] + self.cols)
        df['MEAN'] = df.mean(numeric_only=True, axis=1)
        df['STD'] = df.std(numeric_only=True, axis=1)
        return df

    def similarities(self, list_of_word_pairs):
        """Return the cosine similarities between the pairs of words."""
        base_df = self.list_of_embeddings[0].similarities(list_of_word_pairs)
        base_df = base_df.rename({"Similarity": "Sim_emb1"}, axis=1)
        for idx, emb in enumerate(self.list_of_embeddings[1:]):
            df = emb.similarities(list_of_word_pairs)
            df = df.rename({"Similarity": "Sim_emb" + str(idx+2)}, axis=1)
            base_df = pd.merge(base_df, df, on=['Word1', 'Word2'])

        base_df['MEAN'] = base_df.mean(numeric_only=True, axis=1)
        base_df['STD'] = base_df.std(numeric_only=True, axis=1)
        if self.training_data is not None:
            base_df['Word1_freq'] = [self.frequency_in_training_data(word) for word in base_df['Word1']]
            base_df['Word2_freq'] = [self.frequency_in_training_data(word) for word in base_df['Word2']]
        return base_df

    def projections_to_bipolar_dimensions(self, test, dimensions, normalize_before=True):
        """ Same as the embedding method with the same name, but produces an average of the projections of each ensemble.
        """
        if isinstance(test, str):
            test_words = [test]
        else:
            test_words = test

        # make dimension for each embedding, with only words found in its vocab ===========
        processed_dims = {}
        for dim_name, dim_words in dimensions.items():

            if len(dim_words) != 2 and not (isinstance(dim_words[0], list) and isinstance(dim_words[1], list)):
                raise ValueError("Generating words must be a list of exactly two lists that contain words.")

            processed_dims[dim_name] = {}

            for idx, emb in enumerate(self.list_of_embeddings):

                # LEFT ======================
                # check which dim words cannot be used in this embedding
                left_dim_words_in_emb = []
                left_dim_words_not_in_emb = []
                for dim_word in dim_words[0]:
                    if emb.in_vocab(dim_word):
                        left_dim_words_in_emb.append(dim_word)
                    else:
                        left_dim_words_not_in_emb.append(dim_word)

                if not left_dim_words_in_emb:
                    print(
                        "INFO: None of the left generating words to construct dimension {} found in embedding no {};"
                        "this embedding is not used to compute the ensemble projection for "
                        "this dimension.".format(dim_name, idx))
                    continue

                if left_dim_words_not_in_emb:
                    print("INFO: Left generating word(s) {} not found in vocab of embedding no {}; "
                          "word(s) will not be used to construct the dimension in this "
                          "embedding.".format(left_dim_words_not_in_emb, idx))

                # RIGHT ======================
                # check which dim words cannot be used in this embedding
                right_dim_words_in_emb = []
                right_dim_words_not_in_emb = []
                for dim_word in dim_words[1]:
                    if emb.in_vocab(dim_word):
                        right_dim_words_in_emb.append(dim_word)
                    else:
                        right_dim_words_not_in_emb.append(dim_word)

                if not right_dim_words_in_emb:
                    print(
                        "INFO: None of the right generating words to construct dimension {} found in embedding no {};"
                        "this embedding is not used to compute the ensemble projection for "
                        "this dimension.".format(dim_name, idx))
                    continue

                if right_dim_words_not_in_emb:
                    print("INFO: Right generating word(s) {} not found in vocab of embedding no {}; "
                          "word(s) will not be used to construct the dimension in this "
                          "embedding.".format(right_dim_words_not_in_emb, idx))

                processed_dims[dim_name][idx] = [left_dim_words_in_emb, right_dim_words_in_emb]

        # ===============

        data = []
        for test_word in test_words:

            row = [test_word]
            cols = ["test_word"]

            # get indices of embeddings have test word in vocab
            emb_idx = []
            for idx, emb in enumerate(self.list_of_embeddings):
                if emb.in_vocab(test_word):
                    emb_idx.append(idx)

            # kick test word out if it is in no embedding
            if not emb_idx:
                print("INFO: Test word {} is not in vocab of any embedding in the ensemble "
                      "and has been removed from the list of results.".format(test_word))
                continue

            # notify user which embeddings are used
            not_in = set(range(len(self.list_of_embeddings))) - set(emb_idx)
            if not_in:
                print("INFO: Test word {} not found in vocab of embedding number(s) {}; "
                      "embedding(s) will not be used to compute the projection "
                      "of the test word.".format(test_word, not_in))

            # =========================================

            for dim_name, dim_dict in dimensions.items():

                results = []
                for idx in emb_idx:
                    if idx in processed_dims[dim_name]:

                        emb = self.list_of_embeddings[idx]
                        test_vec = emb.vector(test_word)
                        centroid_left = emb.centroid_of_vectors(processed_dims[dim_name][idx][0])
                        centroid_right = emb.centroid_of_vectors(processed_dims[dim_name][idx][1])
                        diff = centroid_left - centroid_right

                        if normalize_before:
                            diff = normalize_vector(diff)

                        res = np.dot(test_vec, diff)
                        results.append(res)

                row.extend([np.mean(results), np.std(results)])

            data.append(row)

        # make correct col names
        for dim in list(dimensions):
            cols.extend([dim, dim + "(std)"])

        df = pd.DataFrame(data, columns=cols)
        df = df.sort_values(cols[1:], axis=0, ascending=False)
        return df

    def projections_to_unipolar_dimensions(self, test, dimensions, normalize_before=True):
        """Same as the embedding method with the same name, but produces an average of the projections of each ensemble.
        """
        if isinstance(test, str):
            test_words = [test]
        else:
            test_words = test

        # make dimension for each embedding, with only words found in its vocab ===========
        processed_dims = {}
        for dim_name, dim_words in dimensions.items():

            if len(np.array(dim_words).shape) != 1:
                raise ValueError("Generating words must be a list of words.")

            processed_dims[dim_name] = {}

            for idx, emb in enumerate(self.list_of_embeddings):

                # check which dim words cannot be used in this embedding
                dim_words_in_emb = []
                dim_words_not_in_emb = []
                for dim_word in dim_words[0]:
                    if emb.in_vocab(dim_word):
                        dim_words_in_emb.append(dim_word)
                    else:
                        dim_words_not_in_emb.append(dim_word)

                if not dim_words_in_emb:
                    print(
                        "INFO: None of the generating words to construct dimension {} found in embedding no {};"
                        "this embedding is not used to compute the ensemble projection for "
                        "this dimension.".format(dim_name, idx))
                    continue

                if dim_words_not_in_emb:
                    print("INFO: Generating word(s) {} not found in vocab of embedding no {}; "
                          "word(s) will not be used to construct the dimension in this "
                          "embedding.".format(dim_words_not_in_emb, idx))


                processed_dims[dim_name][idx] = dim_words_in_emb

        # ===============

        data = []
        for test_word in test_words:

            row = [test_word]
            cols = ["test_word"]

            # get indices of embeddings have test word in vocab
            emb_idx = []
            for idx, emb in enumerate(self.list_of_embeddings):
                if emb.in_vocab(test_word):
                    emb_idx.append(idx)

            # kick test word out if it is in no embedding
            if not emb_idx:
                print("INFO: Test word {} is not in vocab of any embedding in the ensemble "
                      "and has been removed from the list of results.".format(test_word))
                continue

            # notify user which embeddings are used
            not_in = set(range(len(self.list_of_embeddings))) - set(emb_idx)
            if not_in:
                print("INFO: Test word {} not found in vocab of embedding number(s) {}; "
                      "embedding(s) will not be used to compute the projection "
                      "of the test word.".format(test_word, not_in))

            # =========================================

            for dim_name, dim_dict in processed_dims.items():

                results = []
                for idx in emb_idx:
                    if idx in processed_dims[dim_name]:

                        emb = self.list_of_embeddings[idx]
                        test_vec = emb.vector(test_word)
                        centroid = emb.centroid_of_vectors(processed_dims[dim_name][idx])

                        if normalize_before:
                            centroid = normalize_vector(centroid)
                        res = np.dot(test_vec, centroid)
                        results.append(res)

                row.extend([np.mean(results), np.std(results)])

            data.append(row)

        # make correct col names
        for dim in list(dimensions):
            cols.extend([dim, dim + "(std)"])

        df = pd.DataFrame(data, columns=cols)
        df = df.sort_values(cols[1:], axis=0, ascending=False)
        return df

