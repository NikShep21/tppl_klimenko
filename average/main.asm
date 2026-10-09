global _start

%define BUFFER_SIZE 65536

section .data
    separator db ": ", 0
    bad_msg   db ": файл испорчен", 10, 0
    newline   db 10, 0

section .bss
    buffer  resb BUFFER_SIZE + 1
    num_buf resb 24

section .text

print_string:
    xor edx, edx
.len:
    cmp byte [rsi + rdx], 0
    je .write
    inc rdx
    jmp .len
.write:
    mov eax, 1
    mov edi, 1
    syscall
    ret

print_number:
    xor r8d, r8d
    test rax, rax
    jns .convert
    neg rax
    mov r8d, 1
.convert:
    lea rsi, [rel num_buf + 24]
    mov r9d, 10
.digit:
    xor edx, edx
    div r9
    add dl, '0'
    dec rsi
    mov [rsi], dl
    test rax, rax
    jnz .digit
    test r8d, r8d
    jz .write
    dec rsi
    mov byte [rsi], '-'
.write:
    lea rdx, [rel num_buf + 24]
    sub rdx, rsi
    mov eax, 1
    mov edi, 1
    syscall
    ret

_start:
    cmp qword [rsp], 2
    jne .exit_error
    mov r12, [rsp + 16]

    mov eax, 2
    mov rdi, r12
    xor esi, esi
    xor edx, edx
    syscall
    test rax, rax
    js .corrupted
    mov r13, rax

    xor eax, eax
    mov rdi, r13
    lea rsi, [rel buffer]
    mov edx, BUFFER_SIZE
    syscall
    test rax, rax
    jle .close_corrupted
    mov rbx, rax

    cmp rbx, BUFFER_SIZE
    jne .close_file
    xor eax, eax
    mov rdi, r13
    lea rsi, [rel buffer + BUFFER_SIZE]
    mov edx, 1
    syscall
    test rax, rax
    jnz .close_corrupted

.close_file:
    mov eax, 3
    mov rdi, r13
    syscall
    mov byte [buffer + rbx], 0

    lea rsi, [rel buffer]
    xor r13d, r13d
    xor r14d, r14d
    xor r15d, r15d
    xor ebp, ebp

.next_number:
    cmp byte [rsi], ' '
    je .skip_before
    cmp byte [rsi], 9
    jne .sign
.skip_before:
    inc rsi
    jmp .next_number

.sign:
    xor r8d, r8d
    cmp byte [rsi], '-'
    jne .first_digit
    mov r8d, 1
    inc rsi

.first_digit:
    movzx ecx, byte [rsi]
    sub ecx, '0'
    cmp ecx, 9
    ja .corrupted
    xor eax, eax

.digits:
    movzx ecx, byte [rsi]
    sub ecx, '0'
    cmp ecx, 9
    ja .number_ready
    imul rax, rax, 10
    add rax, rcx
    inc rsi
    jmp .digits

.number_ready:
    test r8d, r8d
    jz .save_number
    neg rax
.save_number:
    test r13d, r13d
    jnz .save_y
    add r14, rax
    inc r15
    jmp .after_number
.save_y:
    sub r14, rax
    inc rbp

.after_number:
    cmp byte [rsi], ' '
    je .skip_after
    cmp byte [rsi], 9
    jne .separator
.skip_after:
    inc rsi
    jmp .after_number

.separator:
    cmp byte [rsi], ','
    je .comma
    cmp byte [rsi], 10
    je .line_feed
    cmp byte [rsi], 13
    je .carriage_return
    cmp byte [rsi], 0
    je .file_end
    jmp .corrupted

.comma:
    inc rsi
    jmp .next_number
.carriage_return:
    inc rsi
    cmp byte [rsi], 10
    jne .line_end
.line_feed:
    inc rsi
.line_end:
    test r13d, r13d
    jnz .tail
    mov r13d, 1
    jmp .next_number

.file_end:
    test r13d, r13d
    jz .corrupted
    jmp .calculate

.tail:
    mov al, [rsi]
    test al, al
    jz .calculate
    cmp al, ' '
    je .skip_tail
    cmp al, 9
    je .skip_tail
    cmp al, 10
    je .skip_tail
    cmp al, 13
    jne .corrupted
.skip_tail:
    inc rsi
    jmp .tail

.calculate:
    cmp r15, rbp
    jne .corrupted
    mov rax, r14
    cqo
    idiv r15
    mov r13, rax

    mov rsi, r12
    call print_string
    lea rsi, [rel separator]
    call print_string
    mov rax, r13
    call print_number
    lea rsi, [rel newline]
    call print_string
    xor edi, edi
    jmp .exit

.close_corrupted:
    mov eax, 3
    mov rdi, r13
    syscall
.corrupted:
    mov rsi, r12
    call print_string
    lea rsi, [rel bad_msg]
    call print_string
.exit_error:
    mov edi, 1
.exit:
    mov eax, 60
    syscall
