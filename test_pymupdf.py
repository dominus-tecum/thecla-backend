# Save as: fix_parser.py
import fitz
import PyPDF2
import uuid
import sys

def debug_and_fix(pdf_path):
    """Debug the PDF and show what headings would be created"""
    print(f"🔍 DEBUGGING: {pdf_path}")
    print("=" * 70)
    
    # Get font info
    doc = fitz.open(pdf_path)
    all_items = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        size = span["size"]
                        
                        if size > 14.0 and text and text != '•':
                            all_items.append({
                                'text': text,
                                'size': size,
                                'page': page_num + 1
                            })
    
    doc.close()
    
    print(f"Found {len(all_items)} items with font > 14")
    
    # SIMPLE COMBINING: Group by page and similar text
    headings = []
    i = 0
    
    while i < len(all_items):
        current = all_items[i]
        
        # Check if next item should be combined with current
        if (i + 1 < len(all_items) and
            all_items[i + 1]['page'] == current['page'] and
            current['text'].lower() == 'principles of nursing' and
            all_items[i + 1]['text'].lower() == 'assessment'):
            
            # Combine these two
            headings.append('Principles of nursing assessment')
            i += 2  # Skip both
            
        elif (i + 1 < len(all_items) and
              all_items[i + 1]['page'] == current['page'] and
              current['text'].lower() == 'documenting patient assessment' and
              all_items[i + 1]['text'].lower() == 'and record-keeping'):
            
            # Combine these two
            headings.append('Documenting patient assessment and record-keeping')
            i += 2  # Skip both
            
        else:
            # Single item
            headings.append(current['text'])
            i += 1
    
    # Remove duplicates
    seen = set()
    unique_headings = []
    for heading in headings:
        if heading.lower() not in seen:
            seen.add(heading.lower())
            unique_headings.append(heading)
    
    print(f"\n📑 HEADINGS THAT WILL BE CREATED ({len(unique_headings)}):")
    for i, heading in enumerate(unique_headings):
        print(f"  {i+1:2d}. {heading}")
    
    # Now create actual sections
    print("\n" + "=" * 70)
    print("📄 CREATING SECTIONS...")
    
    sections = []
    
    # Extract full text
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text() + "\n\n"
    
    text_lower = full_text.lower()
    
    for heading in unique_headings[:15]:  # Limit to 15 sections
        heading_lower = heading.lower()
        
        # Find heading in text
        pos = text_lower.find(heading_lower)
        if pos == -1:
            continue
        
        # Get content after heading
        content_start = pos + len(heading)
        content = full_text[content_start:content_start + 1000].strip()  # First 1000 chars
        
        if len(content) > 50:
            sections.append({
                'id': str(uuid.uuid4()),
                'text': f"## {heading} ##",
                'options': [content],
                'correct_idx': -1
            })
            print(f"✅ Created section: {heading}")
    
    print(f"\n🎯 TOTAL SECTIONS CREATED: {len(sections)}")
    return sections

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_parser.py <pdf_file>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    sections = debug_and_fix(pdf_file)