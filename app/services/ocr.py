"""
OCR service using PaddleOCR for text extraction from images and PDFs.
Optimized for dense table extraction in medical reports.
"""
import logging
from typing import List

# Lazy imports to avoid Windows multiprocessing issues with uvicorn reload
# from paddleocr import PaddleOCR  # Imported inside class __init__
from pdf2image import convert_from_bytes
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class OCRService:
    """Service for performing OCR on medical reports with table optimization."""
    
    def __init__(self):
        """Initialize PaddleOCR with optimized parameters for table extraction."""
        try:
            # Lazy import to avoid Windows multiprocessing issues
            from paddleocr import PaddleOCR
            
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                # Detection parameters - VERY aggressive for tables
                det_db_thresh=0.2,          # Even lower threshold for faint table lines
                det_db_box_thresh=0.3,      # Lower box threshold
                det_db_unclip_ratio=2.0,    # Higher ratio to merge text aggressively
                det_limit_side_len=1920,    # Process at higher resolution
                det_limit_type='max',       # Max side length
                # Recognition parameters
                rec_batch_num=6,            # Process more in batch
                drop_score=0.3              # Lower threshold for text confidence
            )
            logger.info("PaddleOCR initialized successfully with table-optimized parameters")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {str(e)}")
            raise
    
    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Extract text from an image using PaddleOCR.
        
        Args:
            image_bytes: Image file content as bytes
            
        Returns:
            Extracted text as a single string
            
        Raises:
            Exception: If OCR processing fails
        """
        try:
            # Verify we have data
            if not image_bytes or len(image_bytes) == 0:
                raise ValueError("Empty image bytes provided")
            
            # Convert bytes to numpy array for OpenCV
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                raise ValueError("Failed to decode image - file may be corrupted")
            
            # Verify image dimensions
            if img.shape[0] == 0 or img.shape[1] == 0:
                raise ValueError("Invalid image dimensions")
            
            logger.info(f"Image loaded successfully: {img.shape[1]}x{img.shape[0]} pixels")
            
            # Preprocess image for better table detection
            img = self._preprocess_image(img)
            
            # Perform OCR
            result = self.ocr_engine.ocr(img)
            
            # Debug: Print result structure
            logger.info(f"OCR result type: {type(result)}, length: {len(result) if result else 0}")
            if result and len(result) > 0:
                logger.info(f"First result element type: {type(result[0])}, length: {len(result[0]) if result[0] else 0}")
            
            # Extract text from result
            extracted_text = self._parse_ocr_result(result)
            
            if not extracted_text:
                logger.warning("OCR completed but no text was extracted")
            else:
                logger.info(f"Extracted {len(extracted_text)} characters from image")
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error during image OCR: {str(e)}")
            raise Exception(f"OCR failed for image: {str(e)}")
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extract text from a PDF by converting pages to images and running OCR.
        Uses high DPI (300) for better text detection in tables.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Extracted text from all pages as a single string
            
        Raises:
            Exception: If PDF processing or OCR fails
        """
        try:
            # Verify we have data
            if not pdf_bytes or len(pdf_bytes) == 0:
                raise ValueError("Empty PDF bytes provided")
            
            # Convert PDF pages to images at HIGH DPI for better table detection
            images = convert_from_bytes(pdf_bytes, dpi=300)
            
            if not images or len(images) == 0:
                raise ValueError("PDF conversion produced no images - file may be corrupted or empty")
            
            logger.info(f"Converted PDF to {len(images)} images at 300 DPI")
            
            all_text = []
            
            for i, image in enumerate(images):
                # Convert PIL Image to OpenCV format
                img_array = np.array(image)
                img_cv2 = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
                # Verify conversion worked
                if img_cv2 is None or img_cv2.shape[0] == 0 or img_cv2.shape[1] == 0:
                    logger.warning(f"Page {i+1} conversion failed, skipping")
                    continue
                
                logger.info(f"Processing page {i+1}/{len(images)} ({img_cv2.shape[1]}x{img_cv2.shape[0]} pixels)")
                
                # Preprocess image for better table detection
                img_cv2 = self._preprocess_image(img_cv2)
                
                # Perform OCR
                result = self.ocr_engine.ocr(img_cv2)
                
                # Debug: Print result structure for first page
                if i == 0:
                    logger.info(f"OCR result type: {type(result)}, length: {len(result) if result else 0}")
                    if result and len(result) > 0:
                        logger.info(f"First result element type: {type(result[0])}, length: {len(result[0]) if result[0] else 0}")
                
                # Extract text
                page_text = self._parse_ocr_result(result)
                
                if page_text:
                    all_text.append(f"--- Page {i+1} ---\n{page_text}")
                else:
                    logger.warning(f"No text extracted from page {i+1}")
            
            if not all_text:
                logger.warning("No text extracted from any PDF page")
                return ""
            
            full_text = "\n\n".join(all_text)
            logger.info(f"Total extracted text length: {len(full_text)} characters from {len(all_text)} pages")
            
            return full_text
            
        except Exception as e:
            logger.error(f"Error during PDF OCR: {str(e)}")
            raise Exception(f"OCR failed for PDF: {str(e)}")
    
    def _preprocess_image(self, img):
        """
        Preprocess image to improve OCR accuracy for tables.
        
        Args:
            img: OpenCV image (numpy array)
            
        Returns:
            Preprocessed image
        """
        # Convert to grayscale if color
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        # Apply adaptive thresholding to handle varying lighting
        # This helps separate text from background in tables
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,  # Block size
            10   # Constant subtracted from mean
        )
        
        # Denoise to remove small artifacts
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
        
        # Convert back to BGR for PaddleOCR (it expects color images)
        processed = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
        
        logger.debug("Image preprocessing complete: grayscale -> adaptive threshold -> denoise")
        
        return processed
    
    def _parse_ocr_result(self, result: List) -> str:
        """
        Parse PaddleOCR result and extract text.
        Joins lines with spaces (not newlines) to keep sentences together for LLM.
        
        Args:
            result: PaddleOCR result structure
            
        Returns:
            Concatenated text from all detected text regions
        """
        if not result:
            logger.warning("OCR result is None or empty")
            return ""
        
        if not result[0]:
            logger.warning("OCR result[0] is None - no text detected")
            return ""
        
        text_lines = []
        for idx, line in enumerate(result[0]):
            try:
                if not line or len(line) < 2:
                    logger.debug(f"Skipping invalid line {idx}: {line}")
                    continue
                
                # line format: [[[x1,y1], [x2,y2], ...], (text, confidence)]
                # OR sometimes: [box, [text, confidence]]
                text_info = line[1] if len(line) > 1 else None
                
                if not text_info:
                    continue
                
                # Extract text - handle both tuple and list formats
                if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                    text = text_info[0]  # Text
                    confidence = text_info[1]  # Confidence score
                elif isinstance(text_info, str):
                    text = text_info
                    confidence = 1.0  # Assume high confidence if not provided
                else:
                    logger.debug(f"Unexpected text_info format at line {idx}: {text_info}")
                    continue
                
                # Only include text with reasonable confidence
                if confidence > 0.5 and text and str(text).strip():
                    text_lines.append(str(text).strip())
                    
            except Exception as e:
                logger.warning(f"Error parsing line {idx}: {e} - Line data: {line}")
                continue
        
        if not text_lines:
            logger.warning("No valid text lines extracted (all below confidence threshold or parsing failed)")
            return ""
        
        logger.info(f"Successfully parsed {len(text_lines)} text lines from OCR result")
        
        # Join with spaces to keep words/sentences together for better LLM processing
        return " ".join(text_lines)


# Singleton instance
_ocr_service = None


def get_ocr_service() -> OCRService:
    """Get or create the OCR service singleton instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


def process_file(file_bytes: bytes, filename: str) -> str:
    """
    Simple wrapper to process a file and extract text.
    Optimized for dense table extraction in medical reports.
    
    Args:
        file_bytes: File content as bytes
        filename: Name of the file to determine type
        
    Returns:
        Extracted text as string
        
    Raises:
        ValueError: If file is empty or invalid
        Exception: If OCR processing fails
    """
    # Verify input
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("Empty file provided - no bytes to process")
    
    if not filename:
        raise ValueError("Filename is required to determine file type")
    
    ocr_service = get_ocr_service()
    
    # Determine file type from extension
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if not file_ext:
        raise ValueError("Could not determine file extension from filename")
    
    logger.info(f"Processing {file_ext.upper()} file: {filename} ({len(file_bytes)} bytes)")
    
    if file_ext == 'pdf':
        return ocr_service.extract_text_from_pdf(file_bytes)
    else:
        return ocr_service.extract_text_from_image(file_bytes)
