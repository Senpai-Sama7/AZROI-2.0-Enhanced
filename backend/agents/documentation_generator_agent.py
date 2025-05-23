import logging
import json
import re
import os
from typing import Dict, Any, List, Optional, Union

class DocumentationGeneratorAgent:
    """
    Agent for generating documentation from code or plans.
    """
    def __init__(self):
        self.logger = logging.getLogger("DocumentationGeneratorAgent")
        self.output_dir = "generated_docs"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, content: str, doc_type: str = "markdown", metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate documentation based on input content
        
        Args:
            content: Source content to document (code, plan, specification)
            doc_type: Output format (markdown, rst, html, json)
            metadata: Optional metadata about the content (title, author, version, etc.)
            
        Returns:
            Generated documentation as a string
        """
        self.logger.info(f"Generating documentation of type: {doc_type}")
        
        if not metadata:
            metadata = {}
            
        title = metadata.get("title", "Generated Documentation")
        version = metadata.get("version", "1.0.0")
        author = metadata.get("author", "Autonomous AI Architect")
        
        try:
            # Different format handlers
            if doc_type.lower() == "markdown":
                doc = self._generate_markdown(content, title, version, author, metadata)
            elif doc_type.lower() == "rst":
                doc = self._generate_rst(content, title, version, author, metadata)
            elif doc_type.lower() == "html":
                doc = self._generate_html(content, title, version, author, metadata)
            elif doc_type.lower() == "json":
                doc = self._generate_json(content, title, version, author, metadata)
            else:
                self.logger.warning(f"Unknown documentation type: {doc_type}, defaulting to markdown")
                doc = self._generate_markdown(content, title, version, author, metadata)
                
            # Optionally save the documentation
            if metadata.get("save", False):
                filename = metadata.get("filename", f"{title.replace(' ', '_').lower()}.{doc_type}")
                file_path = os.path.join(self.output_dir, filename)
                
                with open(file_path, "w") as f:
                    f.write(doc)
                    
                self.logger.info(f"Documentation saved to {file_path}")
                
            return doc
            
        except Exception as e:
            self.logger.error(f"Documentation generation error: {e}")
            return f"ERROR: Failed to generate documentation: {str(e)}"

    def _generate_markdown(self, content: str, title: str, version: str, author: str, metadata: Dict[str, Any]) -> str:
        """Generate Markdown documentation"""
        doc = f"# {title}\n\n"
        
        if version or author:
            doc += "*"
            if version:
                doc += f"v{version}"
            if version and author:
                doc += " | "
            if author:
                doc += f"Author: {author}"
            doc += "*\n\n"
        
        # Add description if provided
        if "description" in metadata:
            doc += f"{metadata['description']}\n\n"
            
        # Table of contents if the content is long
        if len(content) > 1000:
            doc += "## Table of Contents\n"
            
            # Try to extract sections
            section_pattern = re.compile(r'#+\s+(.+)$', re.MULTILINE)
            sections = section_pattern.findall(content)
            
            for section in sections:
                anchor = section.lower().replace(' ', '-')
                doc += f"- [{section}](#{anchor})\n"
            doc += "\n"
            
        # Add the main content
        doc += f"{content}\n\n"
        
        # Add additional sections from metadata
        if "api_endpoints" in metadata:
            doc += "## API Endpoints\n\n"
            for endpoint in metadata["api_endpoints"]:
                doc += f"### {endpoint.get('method', 'GET')} {endpoint.get('path', '/')}\n\n"
                doc += f"{endpoint.get('description', '')}\n\n"
                
        if "examples" in metadata:
            doc += "## Examples\n\n"
            for example in metadata["examples"]:
                doc += f"### {example.get('title', 'Example')}\n\n"
                doc += f"{example.get('description', '')}\n\n"
                if "code" in example:
                    doc += f"```{example.get('language', '')}\n{example['code']}\n```\n\n"
                    
        return doc

    def _generate_rst(self, content: str, title: str, version: str, author: str, metadata: Dict[str, Any]) -> str:
        """Generate ReStructuredText documentation"""
        doc = f"{title}\n{'=' * len(title)}\n\n"
        
        if version or author:
            if version:
                doc += f":Version: {version}\n"
            if author:
                doc += f":Author: {author}\n"
            doc += "\n"
            
        # Add description if provided
        if "description" in metadata:
            doc += f"{metadata['description']}\n\n"
            
        # Add the main content
        doc += f"{content}\n\n"
        
        return doc

    def _generate_html(self, content: str, title: str, version: str, author: str, metadata: Dict[str, Any]) -> str:
        """Generate HTML documentation"""
        doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 900px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        pre {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        code {{ font-family: monospace; }}
        .metadata {{ color: #666; font-style: italic; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
"""
        
        if version or author:
            doc += '    <div class="metadata">\n'
            if version:
                doc += f"        <p>Version: {version}</p>\n"
            if author:
                doc += f"        <p>Author: {author}</p>\n"
            doc += "    </div>\n"
            
        # Add description if provided
        if "description" in metadata:
            doc += f"    <p>{metadata['description']}</p>\n"
            
        # Add the main content (convert markdown to HTML)
        # This is a simple conversion, for production use a proper Markdown->HTML converter
        paragraphs = content.split("\n\n")
        for paragraph in paragraphs:
            if paragraph.strip().startswith("# "):
                # H1 heading
                doc += f"    <h1>{paragraph.strip()[2:]}</h1>\n"
            elif paragraph.strip().startswith("## "):
                # H2 heading
                doc += f"    <h2>{paragraph.strip()[3:]}</h2>\n"
            elif paragraph.strip().startswith("### "):
                # H3 heading
                doc += f"    <h3>{paragraph.strip()[4:]}</h3>\n"
            elif paragraph.strip().startswith("```"):
                # Code block
                code_parts = paragraph.strip().split("\n")
                if len(code_parts) > 2:
                    code_content = "\n".join(code_parts[1:-1])
                    doc += f"    <pre><code>{code_content}</code></pre>\n"
            else:
                # Regular paragraph
                doc += f"    <p>{paragraph}</p>\n"
            
        doc += """</body>
</html>"""
            
        return doc

    def _generate_json(self, content: str, title: str, version: str, author: str, metadata: Dict[str, Any]) -> str:
        """Generate JSON documentation"""
        doc_data = {
            "title": title,
            "version": version,
            "author": author,
            "content": content,
            "metadata": metadata
        }
        
        return json.dumps(doc_data, indent=2)

    def auto_generate_from_code(self, code_files: List[Dict[str, str]], output_format: str = "markdown") -> str:
        """
        Automatically generate documentation from code files
        
        Args:
            code_files: List of dictionaries with file info [{"path": "file.py", "content": "code here"}]
            output_format: Documentation format (markdown, rst, html, json)
            
        Returns:
            Generated documentation
        """
        self.logger.info(f"Auto-generating documentation for {len(code_files)} files")
        
        # Extract doc strings, function signatures, classes, etc.
        project_docs = {
            "title": "Code Documentation",
            "files": []
        }
        
        for file_info in code_files:
            file_path = file_info.get("path", "unknown")
            content = file_info.get("content", "")
            
            file_doc = self._extract_code_documentation(file_path, content)
            project_docs["files"].append(file_doc)
            
        # Convert to the desired format
        result = ""
        
        if output_format == "json":
            result = json.dumps(project_docs, indent=2)
        else:
            # Build documentation content
            doc_content = f"# {project_docs['title']}\n\n"
            doc_content += "## Files\n\n"
            
            for file_doc in project_docs["files"]:
                doc_content += f"### {file_doc['file_path']}\n\n"
                
                if file_doc.get("module_docstring"):
                    doc_content += f"{file_doc['module_docstring']}\n\n"
                
                if file_doc.get("classes"):
                    doc_content += "#### Classes\n\n"
                    for cls in file_doc["classes"]:
                        doc_content += f"##### {cls['name']}\n\n"
                        if cls.get("docstring"):
                            doc_content += f"{cls['docstring']}\n\n"
                        
                        if cls.get("methods"):
                            for method in cls["methods"]:
                                doc_content += f"###### `{method['signature']}`\n\n"
                                if method.get("docstring"):
                                    doc_content += f"{method['docstring']}\n\n"
                
                if file_doc.get("functions"):
                    doc_content += "#### Functions\n\n"
                    for func in file_doc["functions"]:
                        doc_content += f"##### `{func['signature']}`\n\n"
                        if func.get("docstring"):
                            doc_content += f"{func['docstring']}\n\n"
            
            # Generate in the requested format
            result = self.generate(doc_content, output_format)
            
        return result

    def _extract_code_documentation(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract documentation elements from code"""
        file_doc = {
            "file_path": file_path,
            "module_docstring": None,
            "classes": [],
            "functions": []
        }
        
        # File extension determines language
        extension = os.path.splitext(file_path)[1].lower()
        
        if extension in ['.py']:
            # Extract Python code documentation
            # Extract module docstring
            module_docstring_match = re.search(r'^"""(.+?)"""', content, re.DOTALL)
            if module_docstring_match:
                file_doc["module_docstring"] = module_docstring_match.group(1).strip()
                
            # Extract classes
            class_pattern = re.compile(r'class\s+(\w+)(?:\((.+?)\))?:\s*(?:"""(.+?)""")?', re.DOTALL)
            for match in class_pattern.finditer(content):
                class_name = match.group(1)
                class_bases = match.group(2) or ""
                class_docstring = match.group(3)
                
                class_info = {
                    "name": class_name,
                    "bases": class_bases,
                    "docstring": class_docstring.strip() if class_docstring else None,
                    "methods": []
                }
                
                # Extract methods
                class_content_start = match.end()
                # Find the class content by indentation
                class_content = ""
                in_class = False
                indent_level = 0  # Initialize with default value
                
                for line in content[class_content_start:].split('\n'):
                    if line.strip() and not in_class:
                        in_class = True
                        indent_level = len(line) - len(line.lstrip())
                        
                    if in_class:
                        if line.strip() and len(line) - len(line.lstrip()) <= indent_level:
                            if not line.strip().startswith(("class", "#")):
                                break
                        class_content += line + '\n'
                
                # Find methods in class content
                method_pattern = re.compile(r'def\s+(\w+)\s*\((.+?)\)(?:\s*->?\s*(.+?))?:\s*(?:"""(.+?)""")?', re.DOTALL)
                for m_match in method_pattern.finditer(class_content):
                    method_name = m_match.group(1)
                    method_params = m_match.group(2)
                    method_return = m_match.group(3)
                    method_docstring = m_match.group(4)
                    
                    method_info = {
                        "name": method_name,
                        "signature": f"{method_name}({method_params})",
                        "return_type": method_return.strip() if method_return else None,
                        "docstring": method_docstring.strip() if method_docstring else None
                    }
                    
                    class_info["methods"].append(method_info)
                
                file_doc["classes"].append(class_info)
                
            # Extract standalone functions
            function_pattern = re.compile(r'def\s+(\w+)\s*\((.+?)\)(?:\s*->?\s*(.+?))?:\s*(?:"""(.+?)""")?', re.DOTALL)
            for match in function_pattern.finditer(content):
                # Ignore if this is inside a class (already processed)
                func_pos = match.start()
                in_class = False
                
                for cls in file_doc["classes"]:
                    if any(m["name"] == match.group(1) for m in cls["methods"]):
                        in_class = True
                        break
                
                if in_class:
                    continue
                
                func_name = match.group(1)
                func_params = match.group(2)
                func_return = match.group(3)
                func_docstring = match.group(4)
                
                func_info = {
                    "name": func_name,
                    "signature": f"{func_name}({func_params})",
                    "return_type": func_return.strip() if func_return else None,
                    "docstring": func_docstring.strip() if func_docstring else None
                }
                
                file_doc["functions"].append(func_info)
        
        return file_doc

    def health_check(self) -> bool:
        """
        Check if the documentation generator is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple test - generate a small doc
            test_doc = self.generate("Test content", "markdown")
            return test_doc.startswith("# ") and "Test content" in test_doc
        except Exception as e:
            self.logger.error(f"Documentation generator health check failed: {e}")
            return False
