import fitz
from pdfminer.high_level import extract_pages
from pdfminer.layout import *
import math
import re
import json
import sys

def extract_sentences_with_starting_words(pdf_path, starting_words):
    doc = fitz.open(pdf_path)
    word_sentences = [[] for _ in range(len(starting_words))]
    current_word = None
    previous_line_empty = False
    previous_line_word = None

    # Get footers to check later if line is a footer
    footers = get_footers(doc)

    for page in doc:
        text = page.get_text()
        lines = text.splitlines()
        for line in lines:
            if line.strip():  # Check if the line is not empty
                # Check if the line starts with any of the starting words
                for i, word in enumerate(starting_words):
                    if line.lower().startswith(word.lower()) and line[0].isupper():
                        current_word = i
                        word_sentences[current_word].append(line.strip())
                        previous_line_word = i
                        break
                else:
                    # Append the line to the current sentence if a starting word is detected in the previous line
                    if current_word is not None and line not in footers:
                        word_sentences[current_word][-1] += ' ' + line.strip()
                        previous_line_word = current_word
            elif previous_line_word is not None and not previous_line_empty:
                # End the sentence if the current line is empty and the previous line wasn't empty
                current_word = None
                previous_line_word = None

            previous_line_empty = not line.strip()  # Update the flag for the previous line

    doc.close()
    return word_sentences

def get_footers(fitz_doc):
    footers = []
    for page in fitz_doc:
        data = page.get_text("blocks")
        h = page.rect.height

        for l in data:
            if l[1] > 0.90*h:
                text = l[4]
                footers.append(text[:-1]) # remove the newline character at end of footer

    return footers

def concat_strings(input_list):
    result_list = []
    temp_string = ""
    prev_attributes = None

    for item in input_list:
        text, font, size, float_val = item
        attributes = (font, size, float_val)

        if attributes == prev_attributes: # and not re.search(r'Bold', font, re.IGNORECASE):
            if text[0].isupper() and re.search(r'Bold', font, re.IGNORECASE):
                temp_string = text
            else:
                temp_string += " " + text
        else:
            if temp_string:
                result_list.append([temp_string.strip()] + list(prev_attributes))
            temp_string = text
            prev_attributes = attributes

    # Append the last concatenated string
    if temp_string:
        result_list.append([temp_string.strip()] + list(prev_attributes))

    return result_list


def extract_text_by_fontsize(pdf_url):
    extracted_text = ""
    curr_font = None
    curr_size = None
    font_attr = []

    for page_layout in extract_pages(pdf_url):
        for element in page_layout:
            for line in element:
                thisline = []
                if isinstance(line, LTTextLine):
                    for char in line:
                        if isinstance(char, LTChar):
                            ft = char.fontname
                            sz = math.ceil(char.size)
                            x = char.bbox[0]

                            #if ft != curr_font or sz != curr_size:

                            l = line.get_text()
                            thisline.append(l[:-1])
                            thisline.append(ft)
                            thisline.append(sz)
                            thisline.append(x)
                            font_attr.append(thisline)        
                        break

    result_list = concat_strings(font_attr)
    return result_list


def classify_text(font_name, font_size, x):
  # Classification rules here based on font_name, font_size, and y (position)
  if re.search(r'Bold', font_name, re.IGNORECASE) and (font_size > 14 or x > 100):  # Threshold based on PDF
    return "Titre"
  elif re.search(r'Bold', font_name, re.IGNORECASE) and font_size > 13:
    return "Section"
  elif font_size > 8:
    return "Paragraphe"
  else:
    return "Footer"


def process_pdf(pdf_text):
  l2 = []
  for line_attr in pdf_text:
    
    text = line_attr[0]
    font_name = line_attr[1]
    font_size = line_attr[2]
    x = line_attr[3]
    category = classify_text(font_name, font_size, x)
    # Do something with the classified text and category
    #print(f"{text}, Category: {category}")
    map = (category, text)
    l2.append(map)
  return l2


def comp(l1, l2):
    # Convert list1 to a set of sentences for efficient comparison
    set1 = set([(category, sentence) for category, sentence in l1])

    combined_sentences = l1[:]
    
    temp = []
    for c, s in l1:
        temp.append(s)
    
    for category, sentence in l2:
    
        if sentence not in temp:
            combined_sentences.append((category, sentence))

    def sort_key(item):
    # Get the first key in the dictionary and return it
        return next(iter(item))

    # Sort the list of dictionaries
    sorted_data = sorted(combined_sentences, key=sort_key)
    
    return sorted_data    


def make_map(suchi):
    naksha = {}
    for i, (c, s)  in enumerate(suchi):
        naksha[i] = {"Category": c, "Text":s}

    unique_map = {}
    for key, value in naksha.items():
        if value not in unique_map.values():
            unique_map[key] = value

    res = {}
    i = 0
    for key, value in unique_map.items():
        res[i] = value
        i += 1
    
    return res

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Command: python main.py <pdf path>")
        sys.exit(1)
    pdf_path = sys.argv[1]

    starting_words = ["Titre", "Title", "Chapitre", "Chapter", "Section", "Sous-section","Sub-section", "Paragraphe","Paragraph" ,"Article", "Livre", "Book" ]
    # Extract sentences with specified starting words
    word_sentences = extract_sentences_with_starting_words(pdf_path, starting_words)

    l1 = []
    for i, word in enumerate(starting_words):
        for sentence in word_sentences[i]:
            map = (word, sentence)
            l1.append(map)

    pdf_text = extract_text_by_fontsize(pdf_path)
    l2 = process_pdf(pdf_text)
    
    compare = comp(l1,l2)
    naksha = make_map(compare)

    outfile = open("output_standardization.json", "w", encoding = 'utf-8') 
    json.dump(naksha, outfile,indent=2, ensure_ascii=False)
    outfile.close()