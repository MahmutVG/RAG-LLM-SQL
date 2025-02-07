from markitdown import MarkItDown

def pdf2markdown(pdf_file, markdown_file):
    mid = MarkItDown()
    result = mid.convert(pdf_file)
    with open(markdown_file, 'w') as f:
        f.write(result.text_content)

    

if __name__ == '__main__':
    pdf2markdown('/Users/mahmutguney/Downloads/pg.pdf', 'test.md')