import re

class GeoChunker:
    def __init__(self, max_tokens=512):
        self.max_tokens = max_tokens

    def chunk(self, markdown_text: str, doc_id: str, page: int) -> list[dict]:
        """
        Specialized chunking rules for geological texts.
        """
        chunks = []
        
        # Split by empty lines, but try to keep tables and formulas intact
        blocks = re.split(r'\n\s*\n', markdown_text)
        current_chunk = []
        current_len = 0
        
        for block in blocks:
            # Check if block is a table or latex formula
            is_table = '|' in block and '-|-' in block
            is_formula = '$$' in block or '$' in block
            
            # Rule: Always keep tables together if possible, or split by rows if massive
            # Rule: Don't break formulas
            
            # Simplified MVP heuristic
            if current_len + len(block) > self.max_tokens * 4 and not is_table and not is_formula:
                # Flush
                chunks.append({
                    "chunk_id": f"{doc_id}_{page}_{len(chunks)}",
                    "doc_id": doc_id,
                    "page_num": page,
                    "content": "\n\n".join(current_chunk)
                })
                current_chunk = [block]
                current_len = len(block)
            else:
                current_chunk.append(block)
                current_len += len(block)
                
        if current_chunk:
            chunks.append({
                "chunk_id": f"{doc_id}_{page}_{len(chunks)}",
                "doc_id": doc_id,
                "page_num": page,
                "content": "\n\n".join(current_chunk)
            })
            
        return chunks
