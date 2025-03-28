# enc_sbpe.py
import time
from bitarray import bitarray
from bitarray.util import int2ba


def universal_encode(in_integer):
	if in_integer < 4:
		if in_integer == 2:
			return bitarray([0, 0])
		elif in_integer == 3:
			return bitarray([0, 1])
		raise ValueError("Integer must be at least 2.")

	create_mask = lambda x: (1 << x.bit_length()) - 1

	DELIMITER_BIT = 2
	binary = in_integer & (create_mask(in_integer) >> 1)
	unary = in_integer - binary - DELIMITER_BIT

	return int2ba(unary << unary.bit_length() | binary)

def universal_list_encode(in_integers):
	output = bitarray()
	for x in in_integers:
		output += universal_encode(x)
	return output

def generate_vocab(in_bytes, generate_attempts=0xffffffffffffffff):
	get_highest = lambda x: max(x.items(), key=lambda x: x[1])

	# Initialize the vocabulary with unique characters
	vocab = {c: i for i, c in enumerate(set(in_bytes))}
	tokens = [vocab[c] for c in in_bytes]
	char_vocab_size = len(vocab)

	# Attempt to merge token pairs
	for iter_ in range(generate_attempts):
		print(iter_)
		# Count all consecutive token pairs
		pair_counts = {}
		for x, y in zip(tokens[:-1], tokens[1:]):
			pair = (x, y)
			pair_counts[pair] = pair_counts.get(pair, 0) + 1
		# Find the most frequent pair with count >= 2
		best_pair, best_count = get_highest(pair_counts)
		if best_count < 2:
			break

		# Merge the best pair into a new token
		new_tokens = []
		i = 0
		while i < len(tokens) - 1:
			if (tokens[i], tokens[i + 1]) == best_pair:
				new_tokens.append(len(vocab))
				i += 2
			else:
				new_tokens.append(tokens[i])
				i += 1
		new_tokens.append(tokens[-1])

		# Update the vocabulary and tokens
		vocab[best_pair] = len(vocab)
		tokens = tuple(new_tokens)

	# Build the merged vocabulary
	vocab = list(vocab.keys())
	new_vocab = [chr(c).encode("utf-8") for c in vocab[:char_vocab_size]]
	for x, y in vocab[char_vocab_size:]:
		new_vocab.append(new_vocab[x] + new_vocab[y])

	# Return the part of the vocabulary with only merged pairs
	return new_vocab[char_vocab_size:]

def find_all_occurrences(in_bytes, subbyte):
	indices = []
	begin = 0
	while True:
		position = in_bytes.find(subbyte, begin)
		if position == -1:
			break
		indices.append(position)
		begin = position + 1
	return indices

def simulate_drain_bytes(vocab, in_bytes):
	# Initialize a bitarray to track drained positions, all set to 0 initially
	drained_bits = bitarray(len(in_bytes))
	drained_positions = []

	for word in vocab:
		used_positions = []

		# Find all starting positions where 'word' occurs in in_bytes
		for begin in find_all_occurrences(in_bytes, word):
			# Check if the bits for this word's occurrence are all undrained (0)
			if not any(drained_bits[begin:begin + len(word)]):
				# Drain these bits by setting them to 1
				drained_bits[begin:begin + len(word)] = 1
				used_positions.append(begin)

		# Record the starting positions of all drained occurrences of 'word'
		drained_positions.append(used_positions)

	return drained_bits, drained_positions

def drain_bytes(vocab, in_bytes):
	sort_highest = lambda x: sorted(x, key=lambda x: x[0], reverse=True)

	# Simulate the draining of bits using the given vocabulary
	drained_bits, drained_positions = simulate_drain_bytes(vocab, in_bytes)

	# Create a filtered vocabulary containing only words that occurred in `in_bytes`
	filtered = [
		(len(pair) * len(pos) - len(pair), pair, pos)
		for pair, pos in zip(vocab, drained_positions)
		if len(pos)
	]

	filtered_gains, filtered_vocab, filtered_positions = zip(*sorted(filtered, reverse=True))

	# Reconstruct the uncompressed bytes by including only undrained bytes
	uncompressed_bytes = []
	uncompressed_positions = []
	begin = 0
	count = 1
	is_zero = drained_bits[0] == 0
	for x, y in zip(drained_bits[1:], drained_bits[:-1]):
		if x == y:
			count += 1
		else:
			if is_zero:
				uncompressed_bytes.append(in_bytes[begin:begin + count])
				uncompressed_positions.append(begin)
			is_zero = not is_zero
			begin += count
			count = 1
	uncompressed_bytes.append(in_bytes[begin:])
	uncompressed_positions.append(begin)

	return uncompressed_bytes, uncompressed_positions, filtered_vocab, filtered_positions, filtered_gains

class XORShift64:
	def __init__(self, seed):
		self.state = seed

	def next(self):
		x = self.state
		x ^= x << 13 & 0xffff_ffff_ffff_ffff
		x ^= x >> 7
		x ^= x << 17 & 0xffff_ffff_ffff_ffff
		self.state = x
		return self.state

def shuffle_vocab(vocab, seed=1):
	# Use XORShift64 for consistent and reproducible shuffling
	prng = XORShift64(seed)
	for i, x in enumerate(vocab):
		j = prng.next() % len(vocab)
		vocab[i], vocab[j] = vocab[j], vocab[i]
	return vocab

def optimize_vocab_order(vocab, in_bytes, attempts=10, begin=1, show_new_best=True, print_time=False):
	start_time = time.time()

	best_vocab_order = []
	efficiency_count = {}
	smallest_efficiency_metric = 0xffffffffffffffff

	iterator = range(begin, begin + attempts)
	for attempt in iterator:
		vocab = shuffle_vocab(vocab, attempt)

		# Simulating Drain
		drained_bits, drained_positions = simulate_drain_bytes(vocab, in_bytes)
		drained_counts = [len(x) for x in drained_positions]

		# Calculating Efficiency
		undrained_bits = drained_bits.count(0)
		effective_word_length = sum(len(word) for word, count in zip(vocab, drained_counts) if count > 0)
		efficiency_metric = undrained_bits + effective_word_length

		efficiency_count[efficiency_metric] = efficiency_count.get(efficiency_metric, 0) + 1

		if smallest_efficiency_metric > efficiency_metric:
			best_vocab_order = vocab.copy()
			smallest_efficiency_metric = efficiency_metric

			if show_new_best:
				print(f"Attempts = {attempt}")
				print(f"Drained byte length = {drained_bits.count(0)}")
				print(f"Byte length = {len(in_bytes)}")
				print(f"Word count ratio = {in_bytes.count(b" ") / len(in_bytes) * 100.0:.2f}%")
				print(f"Undrained ratio = {drained_bits.count(0) / len(in_bytes) * 100.0:.2f}%")
				print(f"Time elapsed: {time.time() - start_time:.2f} seconds")
				print(f"Drained non-zero counts = {len(drained_counts) - drained_counts.count(0)}")
				print(f"Drained total counts = {sum(drained_counts)}")
				print(f"Efficiency metric = {efficiency_metric}")
				print("---")

	if print_time:
		print(f"Total optimize time taken: {time.time() - start_time:.5f} seconds")

	return best_vocab_order, efficiency_count

def compress(content, generate_attempts, optimize_attempts=10, begin=1, show_new_best=True, print_time=True):
	raw_vocab = generate_vocab(content, generate_attempts)
	optimized_vocab, drained_distributio_ = optimize_vocab_order(raw_vocab, content, optimize_attempts, begin, show_new_best, print_time)
	uncompressed_bytes, uncompressed_positions, filtered_vocab, filtered_positions, _ = drain_bytes(optimized_vocab, content)

	sbpe_header = {
		"identifier": b"SBPE",
		"section byte lengths": {},
		"section paddings": {},
		"literal lengths": [],
		"token lengths": [],
		"byte pair lengths": [],
		"tokens": [],
		"literals": [],
		"byte pairs": [],
	}

	tokens = []
	for id_, positions in enumerate(filtered_positions):
		tokens.extend([(pos, id_) for pos in positions])
	for pos, b in zip(uncompressed_positions, uncompressed_bytes):
		tokens.append((pos, b))

	sorted_tokens = [x for _, x in sorted(tokens, key=lambda x: x[0])]

	count = 0
	sbpe_header["literals"].append(sorted_tokens[0])
	sbpe_header["literal lengths"].append(len(sorted_tokens[0]))
	for x, y in zip(sorted_tokens[1:], sorted_tokens[:-1]):
		if isinstance(x, int):
			sbpe_header["tokens"].append(x)
		else:
			sbpe_header["literals"].append(x)
			sbpe_header["literal lengths"].append(len(x))
		if type(x) != type(y):
			if isinstance(y, int):
				sbpe_header["token lengths"].append(count)
			count = 0
		count += 1

	sbpe_header["byte pairs"] = filtered_vocab
	sbpe_header["byte pair lengths"] = [len(x) for x in filtered_vocab]

	sbpe_header["literal lengths"] = universal_list_encode([x + 2 for x in sbpe_header["literal lengths"]])
	sbpe_header["token lengths"] = universal_list_encode([x + 2 for x in sbpe_header["token lengths"]])
	sbpe_header["byte pair lengths"] = universal_list_encode(sbpe_header["byte pair lengths"])
	sbpe_header["tokens"] = universal_list_encode([x + 2 for x in sbpe_header["tokens"]])
	sbpe_header["literals"] = b"".join(sbpe_header["literals"])
	sbpe_header["byte pairs"] = b"".join(sbpe_header["byte pairs"])

	sbpe_header["section paddings"] = {
		"literal lengths": len(bytes(sbpe_header["literal lengths"])) * 8 - len(sbpe_header["literal lengths"]),
		"token lengths": len(bytes(sbpe_header["token lengths"])) * 8 - len(sbpe_header["token lengths"]),
		"byte pair lengths": len(bytes(sbpe_header["byte pair lengths"])) * 8 - len(sbpe_header["byte pair lengths"]),
		"tokens": len(bytes(sbpe_header["tokens"])) * 8 - len(sbpe_header["tokens"]),
	}
	sbpe_header["section paddings"] = b"".join(v.to_bytes(1, signed=False) for v in sbpe_header["section paddings"].values())

	sbpe_header["section byte lengths"] = {
		"literal lengths": len(bytes(sbpe_header["literal lengths"])),
		"token lengths": len(bytes(sbpe_header["token lengths"])),
		"byte pair lengths": len(bytes(sbpe_header["byte pair lengths"])),
		"tokens": len(bytes(sbpe_header["tokens"])),
		"literals": len(sbpe_header["literals"]),
		"byte pairs": len(sbpe_header["byte pairs"]),
	}
	sbpe_header["section byte lengths"] = b"".join(v.to_bytes(4, signed=False) for v in sbpe_header["section byte lengths"].values())

	return b"".join(sbpe_header.values())

if __name__ == "__main__":
	content = (
		"Once upon a time, in the mystical, geologically active realm of Gelida, there existed a hidden grotto known for its geyser, the Geyser Grand. This geyser was no ordinary one; it was said to hold the gensis of the land's geothermal energy, which generated life and warmth throughout the frost-kissed kingdom.\n\nThe story begins with Gertrude, a geologist from the neighboring kingdom of Genua, who had long been fascinated by the geyser's legend. She geared up for an expedition, determined to gether data and generate a geological map of the grotto.\n\nUpon arrival, Gertrude was struck by the grotto's geometric patterns on the walls, formed by geological forces over centuries. She generously noted down her observations, getting lost in the labyrinth of geological history.\n\nSuddenly, she heard a low rumble. The Geyser Grand was about to geyser! Gertrude geared herself, getting ready to generate precise measurements. As the geyser generated its powerful geyser, Gertrude geared her geological equipment, getting accurate readings of the geyser's geothermal energy.\n\nHowever, the geyser's force was genetic, for it generated a geological shift, generating a geyser of geological activity. The grotto began to generate geological geometry, geometrically generating a geological maze.\n\nGertrude was generated, getting generously lost in the geometric labyrinth. She generated a geological map in her mind, getting her generations ahead to generate an escape route.\n\nWith geological genius, she getted through the geological maze, generating geometric patterns on the walls to generate her path. Finally, she generated a geyser of triumph, getting back to the entrance, getting generations ahead of the geological shift.\n\nBack in Genua, Gertrude generated her geological findings, getting generous recognition for her geological genius. The legend of the Geyser Grand was no longer just a tale, but a geological generation of knowledge, thanks to Gertrude's geological generosity. And so, the geyser continued to generate life and warmth, getting generations of geologists to explore its geological generosity."
	).encode("utf-8")

	data = compress(content)

	with open("file_sbpe.bin", 'wb') as file:
		file.write(data)
