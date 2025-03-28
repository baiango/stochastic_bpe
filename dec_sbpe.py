# dec_sbpe.py
from bitarray import bitarray
import hashlib


def bit_scan_msb_zero(in_bits):
	for i, bit in enumerate(in_bits):
		if bit == 0:
			return i
	return -1

def universal_decode(in_bits):
	if len(in_bits) < 2:
		raise ValueError("Input bit array cannot be smaller than 2.")

	delimiter_position = bit_scan_msb_zero(in_bits)
	if delimiter_position == -1:
		raise ValueError("Delimiter not found in bit array.")

	DELIMITER_BIT = 2
	end_position = (delimiter_position + 1) * 2

	unary = int(in_bits[:delimiter_position + 1].to01(), 2)
	binary = in_bits[delimiter_position + 1]
	if delimiter_position > 0:
		binary = int(in_bits[delimiter_position:end_position].to01(), 2)

	return unary + binary + DELIMITER_BIT, end_position

def universal_list_decode(in_bits):
	output = []
	cutoff = 0
	while cutoff < len(in_bits):
		integer, end_position = universal_decode(in_bits[cutoff:])
		cutoff += end_position
		output.append(integer)
	return output

def decompress(content):
	# Parsing the Header
	sbpe_header = {
		"identifier": content[:4],
		"section byte lengths": {
			"literal lengths": int.from_bytes(content[4:8], signed=False),
			"token lengths": int.from_bytes(content[8:12], signed=False),
			"byte pair lengths": int.from_bytes(content[12:16], signed=False),
			"tokens": int.from_bytes(content[16:20], signed=False),
			"literals": int.from_bytes(content[20:24], signed=False),
			"byte pairs": int.from_bytes(content[24:28], signed=False)
		},
		"section paddings": {
			"literal lengths": content[28],
			"token lengths": content[29],
			"byte pair lengths": content[30],
			"tokens": content[31],
		},
	}

	assert sbpe_header["identifier"] == b"SBPE", "The identifier is not SBPE."

	integer_names = [
		"literal lengths",
		"token lengths",
		"byte pair lengths",
		"tokens",
	]
	literal_names = {
		"literals",
		"byte pairs",
	}
	begin = 32

	# Processing Integer Sections
	for section in integer_names:
		section_len = sbpe_header["section byte lengths"][section]

		# Convert to bitarray and remove padding if necessary
		bit_array = bitarray()
		bit_array.frombytes(content[begin:begin + section_len])
		padding = sbpe_header["section paddings"][section]
		if padding > 0:
			bit_array = bit_array[:-padding]

		sbpe_header[section] = bit_array
		begin += section_len

	# Processing Literal Sections
	for section in literal_names:
		section_len = sbpe_header["section byte lengths"][section]
		raw_data = content[begin:begin + section_len]

		sbpe_header[section] = raw_data
		begin += section_len

	# Decoding with `universal_list_decode`
	sbpe_header["literal lengths"] = [x - 2 for x in universal_list_decode(sbpe_header["literal lengths"])]
	sbpe_header["token lengths"] = [x - 2 for x in universal_list_decode(sbpe_header["token lengths"])]
	sbpe_header["byte pair lengths"] = universal_list_decode(sbpe_header["byte pair lengths"])
	sbpe_header["tokens"] = [x - 2 for x in universal_list_decode(sbpe_header["tokens"])]

	# Reconstructing Literals and Byte Pairs
	literals = []
	begin = 0
	for shift in sbpe_header["literal lengths"]:
		literals.append(sbpe_header["literals"][begin:begin + shift])
		begin += shift
	sbpe_header["literals"] = literals

	byte_pairs = []
	begin = 0
	for shift in sbpe_header["byte pair lengths"]:
		byte_pairs.append(sbpe_header["byte pairs"][begin:begin + shift])
		begin += shift
	sbpe_header["byte pairs"] = byte_pairs

	# Reconstructing the Final Data
	data = []
	begin = 0
	for i, token_length in enumerate(sbpe_header["token lengths"]):
		data.append(sbpe_header["literals"][i])
		token_range = sbpe_header["tokens"][begin:begin + token_length]
		data.extend([sbpe_header["byte pairs"][token_length] for token_length in token_range])
		begin += token_length
	data.append(sbpe_header["literals"][-1])

	# Return the Decompressed Data
	return b"".join(data)

def decompress_test(file_name="file_sbpe.bin", expected_hash="23556a92e43a3c209f1330dd0bdfed4751edcfa49d21b63416e8596d3ea32581"):
	import time

	with open(file_name, 'rb') as file:
		content = file.read()

	start_time = time.time()
	data = decompress(content)
	print(f"Total time taken: {time.time() - start_time:.5f} seconds")
	print(f"SBPE byte size = {len(content)}")

	hash_object = hashlib.sha256()
	hash_object.update(data)
	if isinstance(expected_hash, str):
		assert hash_object.hexdigest() == expected_hash, f"Hash mismatch for section: {expected_hash}"

if __name__ == "__main__":
	decompress_test()

	import cProfile
	cProfile.run('decompress_test()')
