NASM ?= nasm
LD ?= ld
FILE ?= data.txt

.PHONY: all run clean

all: average

average: main.o
	$(LD) -o $@ $<

main.o: main.asm
	$(NASM) -f elf64 -g -F dwarf -o $@ $<

run: average
	./average "$(FILE)"

clean:
	rm -f main.o average
