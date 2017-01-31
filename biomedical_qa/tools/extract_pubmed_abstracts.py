import tensorflow as tf
import os
import tarfile
import json
import nltk.data
import xml.etree.ElementTree as ET
import logging
from html2text import html2text

tf.app.flags.DEFINE_string('data_dir', None, 'Path to directory containing all tar.gz files.')
tf.app.flags.DEFINE_string('out_json', None, 'Path to the output JSON file.')
tf.app.flags.DEFINE_string('extract', "question_titles", '(question_titles|all_questions).')

FLAGS = tf.app.flags.FLAGS


def iter_xmls(tar):

    members = tar.getmembers()
    for i, member in enumerate(members):

        if i % 10000 == 0:
            print("  Parsing file %d / %d" % (i+1, len(members)))

        if not member.name.endswith(".nxml"):
            continue

        with tar.extractfile(member) as f:
            root = ET.parse(f).getroot()
            f.seek(0)
            xml_text = str(f.read())
            yield root, xml_text, member.name


def process_tarfile_question_titles(tar):

    data = []

    for root, _, filename in iter_xmls(tar):

        title_node = root.find("front/article-meta/title-group/article-title")

        if title_node is None or title_node.text is None:
            logging.warning("No title: %s" % filename)
            continue

        title = title_node.text

        if title is None or title[-1] != "?":
            continue

        abstract_node = root.find("**/abstract")
        if abstract_node is None:
            logging.warning("No abstract: %s" % filename)
            continue
        abstract_xml = ET.tostring(abstract_node).decode("utf-8")

        data.append({
            "id": filename,
            "title": title,
            "abstract_xml": abstract_xml,
        })

    return data


def process_tarfile_all_questions(tar):

    data = []
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

    for _, xml_text, filename in iter_xmls(tar):

        text = html2text(xml_text)
        sentences = tokenizer.tokenize(text)
        questions = [s for s in sentences if s[-1] == "?"]

        for question in questions:
            data.append({
                "filename": filename,
                "question": question,
            })

    return data


def main():

    data = []

    process_tarfile = None
    if FLAGS.extract == "question_titles":
        process_tarfile = process_tarfile_question_titles
    elif FLAGS.extract == "all_questions":
        process_tarfile = process_tarfile_all_questions

    files = [f for f in os.listdir(FLAGS.data_dir) if f.endswith(".tar.gz")]
    for file in files:
        with tarfile.open(os.path.join(FLAGS.data_dir, file)) as f:
            print("Processing tarfile:", file)
            new_data = process_tarfile(f)
            data += new_data
            print("Done processing tarfile %s. %d Questions added." % (file, len(new_data)))

    with open(FLAGS.out_json, "w") as f:
        json.dump({"data": data}, f, indent=2)


main()
