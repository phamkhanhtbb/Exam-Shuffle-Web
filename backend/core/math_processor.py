from lxml import etree
from omml_to_latex import omml_to_latex
from typing import Optional, Tuple

class MathProcessor:
    def __init__(self, nsmap):
        self.nsmap = nsmap

    def process_omml_element(self, element) -> Optional[str]:
        """Convert OMML element to LaTeX"""
        try:
            omml_xml = etree.tostring(element, encoding='unicode')
            return omml_to_latex(omml_xml)
        except Exception as e:
            print(f"OMML conversion failed: {e}")
            return None

    def extract_latex_from_run(self, run_element) -> Optional[str]:
        """Try to find and convert OMML math inside a run"""
        # 1. Direct oMath
        omath_elements = run_element.findall('.//m:oMath', namespaces=self.nsmap)
        
        # 2. If not found, try oMathPara
        if not omath_elements:
            omath_para = run_element.findall('.//m:oMathPara', namespaces=self.nsmap)
            if omath_para:
                omath_elements = omath_para[0].findall('.//m:oMath', namespaces=self.nsmap)
        
        if omath_elements:
            return self.process_omml_element(omath_elements[0])
        
        # 3. Handle MathType OLE objects (w:object) -> mc:AlternateContent
        alt_content_ns = {'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006'}
        alt_omath = run_element.findall('.//mc:Choice//m:oMath', namespaces={**self.nsmap, **alt_content_ns})
        if alt_omath:
            return self.process_omml_element(alt_omath[0])
            
        return None

    def extract_ole_image_bytes(self, obj_element, get_image_data_callback) -> Optional[Tuple[bytes, str]]:
        """
        Try to find embedded image data in WMF/EMF within an OLE object.
        Returns: (img_bytes, rId)
        """
        shape_ns = {'v': 'urn:schemas-microsoft-com:vml'}
        imagedata = obj_element.findall('.//v:imagedata', namespaces=shape_ns)
        for img in imagedata:
            rId = img.get(f"{{{self.nsmap['r']}}}id")
            if rId:
                img_bytes = get_image_data_callback(rId)
                if img_bytes:
                    return img_bytes, rId
        return None
