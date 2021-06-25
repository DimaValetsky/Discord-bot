import nltk
from nltk.stem.lancaster import LancasterStemmer

stemmer = LancasterStemmer()
from tensorflow.keras.models import load_model
import numpy
import tflearn
import tensorflow
import random
import json
import pickle

with open("intents.json") as file:
    data = json.load(file)

try:
    with open("data.pickle", "rb") as f:
        words, labels, training, output = pickle.load(f)
except:
    words = []
    labels = []
    docs_x = []
    docs_y = []

    for intent in data["intents"]:
        for pattern in intent["patterns"]:
            wrds = nltk.word_tokenize(pattern)
            words.extend(wrds)
            docs_x.append(wrds)
            docs_y.append(intent["tag"])

        if intent["tag"] not in labels:
            labels.append(intent["tag"])

    words = [stemmer.stem(w.lower()) for w in words if w != "?"]
    words = sorted(list(set(words)))

    labels = sorted(labels)

    training = []
    output = []

    out_empty = [0 for _ in range(len(labels))]

    for x, doc in enumerate(docs_x):
        bag = []

        wrds = [stemmer.stem(w.lower()) for w in doc]

        for w in words:
            if w in wrds:
                bag.append(1)
            else:
                bag.append(0)

        output_row = out_empty[:]
        output_row[labels.index(docs_y[x])] = 1

        training.append(bag)
        output.append(output_row)

    training = numpy.array(training)
    output = numpy.array(output)

    with open("data.pickle", "wb") as f:
        pickle.dump((words, labels, training, output), f)

try:
    model = tensorflow.keras.models.load_model("saved_model/mymodel")
except:

    tensorflow.compat.v1.reset_default_graph()

    net = tflearn.input_data(shape=[None, len(training[0])])  # входной слой сети
    net = tflearn.fully_connected(net, 8)  # первый слой, используется 8 нейронов
    net = tflearn.fully_connected(net, 8)  # второй слой, используется 8 нейронов
    net = tflearn.fully_connected(net, len(output[0]), activation="softmax")  # выходной слой
    net = tflearn.regression(net)  # регрессия

    model = tflearn.DNN(net)  # обучение сети

    model.fit(training, output, n_epoch=1000, batch_size=8, show_metric=True)  # обучение сети
    model.save("saved_model/mymodel")


def bag_of_words(s, words):
    bag = [0 for _ in range(len(words))]

    s_words = nltk.word_tokenize(s)
    s_words = [stemmer.stem(word.lower()) for word in s_words]

    for se in s_words:
        for i, w in enumerate(words):
            if w == se:
                bag[i] = 1

    return numpy.array(bag)
