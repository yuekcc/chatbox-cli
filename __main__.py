import sys
import os

if __name__ == "__main__":
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    vendor = os.path.join(current_dir, "vendor")
    sys.path.insert(0, vendor)
    sys.path.insert(0, current_dir)

    import lacia
    lacia.main()
