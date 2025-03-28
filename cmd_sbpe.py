# cmd_sbpe.py
import sys
import enc_sbpe
import dec_sbpe

def print_help():
	print("Usage: python cmd_sbpe.py [c/d] <infile> <outfile> [.options]...")
	print("Compress Example: python cmd_sbpe.py c file_str.txt file_sbpe.bin .be8435 .at1")
	print("Decompress Example: python cmd_sbpe.py d file_sbpe.bin file_str.txt")
	print()
	print("<options>")
	print("\t.be[1] : Starting seed of optimize vocabulary attempts")
	print("\t.at[10] : Optimize vocabulary attempts")

def process_command(cmd):
	COMPRESS = 0
	DECOMPRESS = 1

	mode = None
	if cmd[1].lower() == "c":
		mode = COMPRESS
	elif cmd[1].lower() == "d":
		mode = DECOMPRESS

	if mode == None or len(cmd) < 4:
		print_help()
		exit()

	in_file = cmd[2]
	out_file = cmd[3]
	options = {x[:3].lower(): x[3:] for x in cmd[4:]}

	content = None
	with open(in_file, "rb") as file:
		content = file.read()

	print(f"Input Size: {len(content)} bytes")

	out_data = None
	if mode == COMPRESS:
		begin = int(options.get(".be", 1))
		attempts = int(options.get(".at", 500))
		out_data = enc_sbpe.compress(content, attempts, begin, show_new_best=False, print_time=False)
	elif mode == DECOMPRESS:
		out_data = dec_sbpe.decompress(content)

	with open(out_file, 'wb') as file:
		file.write(out_data)

	print(f"{"Compressed" if mode == COMPRESS else "Decompressed"} Size: {len(out_data)} bytes")

if __name__ == "__main__":
	process_command(sys.argv)
