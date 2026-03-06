import markdown

with open('TEXTBOOK.md', 'r', encoding='utf-8') as f:
    md_text = f.read()

html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'codehilite', 'toc'])

style = """
body { font-family: Segoe UI, Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; line-height: 1.7; color: #1a1a1a; }
h1 { color: #1a3a5c; border-bottom: 3px solid #4a90d9; padding-bottom: 10px; }
h2 { color: #2c5282; border-bottom: 2px solid #bee3f8; padding-bottom: 8px; margin-top: 50px; }
h3 { color: #2b6cb0; margin-top: 35px; }
h4 { color: #3182ce; }
code { background: #f0f4f8; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; color: #c7254e; }
pre { background: #1e293b; color: #e2e8f0; padding: 16px 20px; border-radius: 8px; overflow-x: auto; line-height: 1.5; }
pre code { background: none; color: #e2e8f0; padding: 0; font-size: 0.85em; }
table { border-collapse: collapse; width: 100%; margin: 20px 0; }
th { background: #2c5282; color: white; padding: 10px 14px; text-align: left; }
td { border: 1px solid #e2e8f0; padding: 8px 14px; }
tr:nth-child(even) { background: #f7fafc; }
blockquote { border-left: 4px solid #4a90d9; margin: 20px 0; padding: 10px 20px; background: #ebf8ff; }
strong { color: #2d3748; }
hr { border: none; border-top: 2px solid #e2e8f0; margin: 40px 0; }
a { color: #3182ce; }
@media print {
    body { max-width: 100%; margin: 0; }
    pre { background: #f0f4f8 !important; color: #333 !important; border: 1px solid #ccc; }
    pre code { color: #333 !important; }
    th { background: #555 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    tr:nth-child(even) { background: #f5f5f5 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    h1, h2, h3, h4 { page-break-after: avoid; }
    pre, table { page-break-inside: avoid; }
}
"""

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AI Agents, Docker &amp; Real-Time Chat — A Textbook Guide</title>
<style>{style}</style>
</head>
<body>
{html_body}
</body>
</html>
"""

with open('TEXTBOOK.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Created TEXTBOOK.html successfully!")
