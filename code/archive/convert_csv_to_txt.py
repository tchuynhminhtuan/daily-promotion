import csv
import os

def convert_csv_to_txt(input_file, output_file, delimiter=';', output_delimiter='\t'):
    """
    Converts a CSV file to a TXT file.
    
    Args:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to the output TXT file.
        delimiter (str): Delimiter used in the input CSV file. Default is ';'.
        output_delimiter (str): Delimiter to use in the output TXT file. Default is tab.
    """
    try:
        with open(input_file, mode='r', encoding='utf-8', newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            
            with open(output_file, mode='w', encoding='utf-8', newline='') as txtfile:
                writer = csv.writer(txtfile, delimiter=output_delimiter)
                
                for row in reader:
                    writer.writerow(row)
        
        print(f"Successfully converted '{input_file}' to '{output_file}'")
    except Exception as e:
        print(f"Error converting file: {e}")

if __name__ == "__main__":
    # Define input and output paths
    # input_csv_path = '/Users/brucehuynh/Documents/Code_Projects/Daily_Work/Daily_Promotion/content/CPS - 2025-11-23/6-cps-2025-11-23.csv'
    input_csv_path = 'Daily_Promotion/content/FPT-2025-11-23/1-fpt-2025-11-23.csv'
    
    # Create output path by replacing .csv with .txt
    output_txt_path = input_csv_path.replace('.csv', '.txt')
    
    # Check if input file exists
    if os.path.exists(input_csv_path):
        convert_csv_to_txt(input_csv_path, output_txt_path)
    else:
        print(f"Input file not found: {input_csv_path}")
