import sys

# Kodni tekshirish uchun oddiy funksiya
def check_code(code: str):
    try:
        # Dinamik ravishda kodni bajarish
        exec(code)
        return "Code executed successfully!"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    # Kodni komandadan o'qish
    code = sys.argv[1]
    print(check_code(code))
