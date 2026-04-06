def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    fib_sequence = [0, 1]
    while len(fib_sequence) < n:
        fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
    return fib_sequence

n = 20
fib_numbers = fibonacci(n)
fib_sum = sum(fib_numbers)

print(f"{'Index':<10} | {'Fibonacci Number':<20}")
print("-" * 35)
for i, num in enumerate(fib_numbers):
    print(f"{i+1:<10} | {num:<20}")

print("-" * 35)
print(f"{'Sum':<10} | {fib_sum:<20}")