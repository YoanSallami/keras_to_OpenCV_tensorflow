import keras
import os
import sys
import argparse
import os.path as osp
import tensorflow as tf

from keras.models import load_model

from tensorflow.python.framework import graph_util
from tensorflow.python.framework import graph_io
from tensorflow.python.tools.optimize_for_inference_lib import optimize_for_inference
from tensorflow.python.framework import dtypes


def create_output_folder(output_folder):
	# create output directory
	if not os.path.isdir(output_folder):
	    os.mkdir(output_folder)
	return output_folder


def load_keras_model(model_json_file_path, weights_file_path):
	# load keras model
	with open(model_file_path, 'r') as json_file:
		loaded_model_json = json_file.read() # read json file
		net_model = keras.models.model_from_json(loaded_model_json) # create model from json
		net_model.load_weights(weights_file_path) # load weigths to model
		return net_model
	return None


def generate_nodes_names(basename, num_layer_nodes):
	return [ basename + "_" + str(i) for i in range(num_layer_nodes) ]


def set_input_node_names(net_model, node_names):
	for i, node_name in enumerate(node_names):
		tf.identity(net_model.inputs[i], name=node_name) # setup node name
	return net_model


def set_output_node_names(net_model, node_names):
	for i, node_name in enumerate(node_names):
		tf.identity(net_model.outputs[i], name=node_name) # setup node name
	return net_model


def write_graph_def_in_ascii(sess, output_folder):
    filename = 'graph_def.pb.ascii'
    tf.train.write_graph(sess.graph.as_graph_def(), output_folder, filename, as_text=True)
    print('Saved graph definition in ascii format at: ', osp.join(output_folder, filename))



def set_model_node_names(net_model, input_nodes_name, output_nodes_name):

	input_nodes_names = generate_nodes_names(input_nodes_name, len(net_model.inputs))
	output_nodes_names = generate_nodes_names(output_nodes_name, len(net_model.outputs))

	net_model = set_input_node_names(net_model, input_nodes_names)
	net_model = set_output_node_names(net_model, output_nodes_names)

	return net_model, input_nodes_names, output_nodes_names


def parse_args():
	"""Parses command line arguments."""
	parser = argparse.ArgumentParser()
	parser.register("type", "bool", lambda v: v.lower() == "true")

	parser.add_argument(
		"--input_model",
		type=str,
		required=True,
		help="Keras model as a json file that we want to trasnform into a tensorflow buffer and optimize for Opencv Dnn.")
	parser.add_argument(
		"--input_weigths",
		type=str,
		required=True,
		help="Keras weigths file (.h5) that contains the weigths of out Keras model.")
	parser.add_argument(
		"--output_dir",
		type=str,
		required=True,
		help="Directory where you want the output results to be saved.")
	parser.add_argument(
		"--output_name",
		type=str,
		default="model.pb",
		help="Name for the resulting tensorflow buffer (.pb).")
	parser.add_argument(
		"--ascii",
		type=bool,
		default=True,
		help="Do you want to saved the graph definition as a ascii file.")
	parser.add_argument(
		"--output_nodes_name",
		type=str,
		default="output",
		help="Name that will be assign to the output nodes.")
	parser.add_argument(
		"--input_nodes_name",
		type=str,
		default="input",
		help="Name that will be assign to the input nodes.")

	return parser.parse_args()


if __name__ == '__main__':

	# parse args
	ARGS = parse_args()

	# Sets the learning phase to a fixed value.
	keras.backend.set_learning_phase(0)

	# load model from json file and load weigths
	net_model = load_keras_model(ARGS.input_model, ARGS.input_weigths)

	if net_model == None:
		print('Model can not be loaded')
		sys.exit()

	# set names for input and output nodes of the model
	net_model, input_nodes_names, output_nodes_names = set_model_node_names(net_model, ARGS.input_nodes_name, ARGS.output_nodes_name)

	# get sesssion
	sess = keras.backend.get_session()

	output_folder = create_output_folder(ARGS.output_dir)

	if ARGS.ascii:
		write_graph_def_in_ascii(sess, output_folder)

	# freeze graph: trasnform variable placeholders into constants
	constant_graph = graph_util.convert_variables_to_constants(sess, sess.graph.as_graph_def(), output_nodes_names)

	# optimze for inference, eliminate useless layes and other stuff
	# this is requiered otherwise wont work with opencv dnn which doesnt have unnecesary layers implemented
	constant_graph = optimize_for_inference(constant_graph, input_nodes_names, output_nodes_names, dtypes.float32.as_datatype_enum)

	# save graph to output file
	graph_io.write_graph(constant_graph, output_folder, ARGS.output_name, as_text=False)
	print('Saved constant graph (ready for inference) at: ', osp.join(output_folder, ARGS.output_name))

