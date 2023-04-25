import csv
import fitz
import re
from config import config

def highlight_punctuation_errors(input_file:str, pages:list=None):
    comment_name = "Punctuation Error Highlighter"
    # create matches list for output summary
    error_summary = []
    # open pdf
    pdfIn = fitz.open(input_file)
    # Iterate throughout pdf pages
    for pg, page in enumerate(pdfIn):
        pageID = pg+1
        # If required to look in specific pages
        if pages and pageID not in pages:
              continue

        # Get all the text in the page
        text = page.get_text("text")
        target_chars = check_punctuation_errors(text, error_summary)

        page_highlights = {}  # Initialize a dictionary to store match rectangles for each character
        get_positions(target_chars, text, page, page_highlights)
        add_highlight_annot(page_highlights, page, comment_name)

    export_summary(error_summary)
    save_output_file(input_file, pdfIn)

def check_punctuation_errors(text, summary):
    errors = set()
    patterns = [
        (r"[a-zA-Z0-9][.!?]\s{2}"), # Double space after punctuation,
        (r"['\"]"), # Straight quotes
        (r"\s[.,;:?!'\[\]{}()“”‘’&%$¥—-]\s"), # Space before and after punctuation
        (r'\s["’”](?=[a-zA-Z0-9])'), # Space before closing quotation mark followed by a character
        (r"[.,;:?!'\[\]{}()“”‘’&%$¥—-][.,;:?!'\[\]{}()“”‘’&%$¥—-]") # Same punctuation is used twice in a row
    ]
    for pattern in patterns:
        compiled_pattern = re.compile(pattern)
        for match in compiled_pattern.finditer(text):
            error_char = match.group()
            errors.add(error_char)
            update_summary(summary, error_char)
    return errors

def update_summary(summary:list, char):
    found = False
    for entry in summary:
        if entry['char'] == char:
            entry['count'] += 1
            found = True
            break
    if not found:
        summary.append({'char': char, 'count': 1})

def get_positions(target_chars, text, page, page_highlights):
    for char in target_chars:
        start_idx = 0
        while True:
            start_idx = text.find(char, start_idx)
            if start_idx == -1:
                break
            end_idx = start_idx + len(char)
            matches = page.search_for(text[start_idx:end_idx])
            if matches:
                handle_matches(matches, char, page_highlights)
            start_idx += 1

def handle_matches(matches, char, page_highlights):
    for match in matches:
        if char not in page_highlights:
            page_highlights[char] = [match]
        else:
            # Check if the match rectangle is not already in the list
            if not any([rects_are_equal(match, rect) for rect in page_highlights[char]]):
                page_highlights[char].append(match)

def rects_are_equal(rect1, rect2):
    return all([abs(rect1[i] - rect2[i]) < 1e-6 for i in range(4)])

def add_highlight_annot(page_highlights:dict, page, comment_name):
    for char, match_rects in page_highlights.items():
        for rect in match_rects:
            annot = page.add_highlight_annot(rect)
            info = annot.info
            info["title"] = comment_name
            info["content"] = f"Error found: {char}"
            annot.set_info(info)
            annot.update()

def export_summary(error_summary:list):
    fieldnames = ['Character', 'Count']
    with open("error_summary.csv", mode='w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        csv_writer.writeheader()
        for entry in error_summary:
            csv_writer.writerow({
                fieldnames[0]: entry['char'],
                fieldnames[1]: entry['count']
            })

def save_output_file(input_file, pdfIn):
    output_file = input_file.split(".")[0] + " punctuation_errors.pdf"
    pdfIn.save(output_file, garbage=3, deflate=True)
    pdfIn.close()

highlight_punctuation_errors(input_file=config["source_filename"])