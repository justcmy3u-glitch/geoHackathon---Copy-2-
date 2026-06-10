import subprocess
import os

class DjvuConverter:
    def convert_to_pdf(self, djvu_path: str, output_pdf_path: str) -> str:
        """
        Converts DJVU file to PDF using djvulibre (ddjvu command).
        """
        if not os.path.exists(djvu_path):
            raise FileNotFoundError(f"File not found: {djvu_path}")
        
        # ddjvu -format=pdf input.djvu output.pdf
        cmd = ["ddjvu", "-format=pdf", djvu_path, output_pdf_path]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return output_pdf_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to convert DJVU to PDF: {e.stderr.decode('utf-8')}")
