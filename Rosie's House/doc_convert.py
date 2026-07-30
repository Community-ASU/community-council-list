import pypandoc
pypandoc.download_pandoc()

pypandoc.convert_file(
    '/Users/ananthss/seteam/Community_Partner_Document/Rosie\'s House/Rosie\'s House.md', 
    'docx', 
    outputfile='test.docx'
)