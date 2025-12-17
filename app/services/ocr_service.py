"""
OCR service for extracting bank account details from images.
Supports processing screenshots of bank details sent via WhatsApp.
"""

import re
import io
import base64
from typing import Dict, List, Optional, Any, cast
from PIL import Image
import pytesseract
from app.utils.logger import get_logger

logger = get_logger("ocr_service")


class OCRService:
    """OCR service for extracting bank account details from images."""
    
    def __init__(self):
        self.supported_formats = ['jpeg', 'jpg', 'png', 'bmp', 'gif', 'tiff']
        self.bank_patterns = self._load_bank_patterns()
    
    def _load_bank_patterns(self) -> Dict[str, List[str]]:
        """Load bank name patterns for recognition."""
        return {
            'access_bank': ['access bank', 'access bank plc', 'access', 'access bank nigeria'],
            'gtbank': ['gtbank', 'gtb', 'guaranty trust bank', 'guaranty trust', 'gt bank'],
            'first_bank': ['first bank', 'first bank of nigeria', 'first bank plc', 'firstbank'],
            'zenith_bank': ['zenith bank', 'zenith bank plc', 'zenith'],
            'uba': ['uba', 'united bank for africa', 'uba plc'],
            'union_bank': ['union bank', 'union bank of nigeria', 'union bank plc'],
            'fidelity_bank': ['fidelity bank', 'fidelity bank plc', 'fidelity'],
            'fcmb': ['fcmb', 'first city monument bank', 'fcmb plc'],
            'sterling_bank': ['sterling bank', 'sterling bank plc', 'sterling'],
            'stanbic_ibtc': ['stanbic ibtc', 'stanbic ibtc bank', 'stanbic'],
            'wema_bank': ['wema bank', 'wema bank plc', 'wema'],
            'kuda_bank': ['kuda bank', 'kuda', 'kuda microfinance bank'],
            'opay': ['opay', 'opay digital services', 'opay bank'],
            'moniepoint': ['moniepoint', 'moniepoint mfb', 'moniepoint microfinance bank'],
            'palmpay': ['palmpay', 'palmpay limited'],
            'carbon': ['carbon', 'carbon bank'],
            'piggyvest': ['piggyvest', 'piggy bank'],
            'cowrywise': ['cowrywise', 'cowrywise bank'],
        }
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy."""
        try:
            # Resize image if too small
            width, height = image.size
            if width < 800 or height < 600:
                ratio = max(800/width, 600/height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                # Use LANCZOS resampling for better quality
                try:
                    # For newer PIL versions, use Image.Resampling.LANCZOS
                    from PIL import Image
                    try:
                        if hasattr(Image, 'Resampling'):
                            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        else:
                            # Fallback for older PIL versions
                            image = image.resize((new_width, new_height), 1)  # LANCZOS = 1
                    except (AttributeError, ImportError):
                        # Final fallback to BICUBIC
                        try:
                            if hasattr(Image, 'Resampling'):
                                image = image.resize((new_width, new_height), Image.Resampling.BICUBIC)
                            else:
                                image = image.resize((new_width, new_height), 3)  # BICUBIC = 3
                        except (AttributeError, ImportError):
                            # Use NEAREST as last resort
                            try:
                                if hasattr(Image, 'Resampling'):
                                    image = image.resize((new_width, new_height), Image.Resampling.NEAREST)
                                else:
                                    image = image.resize((new_width, new_height), 0)  # NEAREST = 0
                            except (AttributeError, ImportError):
                                # Use default
                                image = image.resize((new_width, new_height))
                except Exception as e:
                    # If all resizing fails, continue with original image
                    logger.warning(f"Image resizing failed: {e}")
            
            # Convert to grayscale for better OCR
            image = image.convert('L')
            
            # Enhance contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            return image
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return image
    
    def _extract_account_number(self, text: str) -> Optional[str]:
        """Extract account number from text."""
        # Nigerian bank account numbers are typically 10 digits
        account_pattern = r'\b\d{10}\b'
        matches = re.findall(account_pattern, text)
        
        if matches:
            # Return the first match
            return cast(str, matches[0])
        
        return None
    
    def _extract_bank_name(self, text: str) -> Optional[str]:
        """Extract bank name from text."""
        text_lower = text.lower()
        
        # Check for bank patterns
        for bank_key, patterns in self.bank_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    # Return the first pattern found (most specific)
                    return pattern.title()
        
        # If no specific pattern found, try to extract bank-like text
        bank_keywords = ['bank', 'microfinance', 'mfb', 'plc', 'limited', 'ltd']
        words = text.split()
        
        for i, word in enumerate(words):
            if any(keyword in word.lower() for keyword in bank_keywords):
                # Try to get the bank name (usually 2-3 words)
                start = max(0, i-2)
                end = min(len(words), i+2)
                potential_bank = ' '.join(words[start:end])
                
                # Clean up the potential bank name
                potential_bank = re.sub(r'[^\w\s]', '', potential_bank)
                
                if len(potential_bank) > 3:
                    return potential_bank.title()
        
        return None
    
    def _extract_account_name(self, text: str) -> Optional[str]:
        """Extract account name from text."""
        # Look for common patterns that indicate account names
        patterns = [
            r'account\s+name[:\s]+([a-zA-Z\s]+)',
            r'name[:\s]+([a-zA-Z\s]+)',
            r'holder[:\s]+([a-zA-Z\s]+)',
            r'customer[:\s]+([a-zA-Z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = re.sub(r'[^\w\s]', '', name)
                name = ' '.join(name.split())  # Remove extra spaces
                
                # Basic validation (name should be 2-50 characters)
                if 2 <= len(name) <= 50 and not name.isdigit():
                    return name.upper()
        
        return None
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract amount from text."""
        # Look for currency patterns
        patterns = [
            r'₦\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'NGN\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'amount[:\s]+(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'balance[:\s]+(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None
    
    async def extract_bank_details(self, image_data: bytes) -> Dict[str, Any]:
        """Extract bank details from image data."""
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(processed_image)
            logger.debug(f"OCR extracted text: {text}")
            
            # Extract information
            account_number = self._extract_account_number(text)
            bank_name = self._extract_bank_name(text)
            account_name = self._extract_account_name(text)
            amount = self._extract_amount(text)
            
            # Prepare result
            result = {
                'success': True,
                'raw_text': text,
                'extracted_data': {
                    'account_number': account_number,
                    'bank_name': bank_name,
                    'account_name': account_name,
                    'amount': amount
                }
            }
            
            # Check if we found the essential information
            if account_number and bank_name:
                result['has_essential_info'] = True
                result['confidence'] = 'high'
            elif account_number or bank_name:
                result['has_essential_info'] = True
                result['confidence'] = 'medium'
            else:
                result['has_essential_info'] = False
                result['confidence'] = 'low'
                result['error'] = 'Could not extract essential bank information'
            
            return result
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'extracted_data': {},
                'has_essential_info': False
            }
    
    async def extract_from_base64(self, base64_data: str) -> Dict[str, Any]:
        """Extract bank details from base64 encoded image."""
        try:
            # Decode base64
            image_data = base64.b64decode(base64_data)
            return await self.extract_bank_details(image_data)
            
        except Exception as e:
            logger.error(f"Base64 decoding failed: {e}")
            return {
                'success': False,
                'error': 'Invalid base64 data',
                'extracted_data': {},
                'has_essential_info': False
            }
    
    def format_extraction_result(self, result: Dict[str, Any]) -> str:
        """Format OCR extraction result for user display."""
        if not result.get('success', False):
            return f"❌ Failed to process image: {result.get('error', 'Unknown error')}"
        
        extracted = result.get('extracted_data', {})
        
        if not result.get('has_essential_info', False):
            return """
🔍 **Image Processed**

I could read the image but couldn't find clear bank details.

Please make sure the image contains:
• Account number (10 digits)
• Bank name clearly visible
• Good lighting and focus

Try again with a clearer image.
"""
        
        # Format the extracted information
        info_parts = []
        
        if extracted.get('account_number'):
            info_parts.append(f"Account Number: {extracted['account_number']}")
        
        if extracted.get('bank_name'):
            info_parts.append(f"Bank: {extracted['bank_name']}")
        
        if extracted.get('account_name'):
            info_parts.append(f"Account Name: {extracted['account_name']}")
        
        if extracted.get('amount'):
            info_parts.append(f"Amount: ₦{extracted['amount']:,.2f}")
        
        confidence = result.get('confidence', 'low')
        confidence_emoji = '🟢' if confidence == 'high' else '🟡' if confidence == 'medium' else '🔴'
        
        info_text = '\n'.join(info_parts)
        
        return f"""
📱 **Image Processed Successfully**

{info_text}

{confidence_emoji} Confidence: {confidence.title()}

Would you like me to resolve this account or make a transfer?
"""
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats."""
        return self.supported_formats
    
    def validate_image_format(self, mime_type: str) -> bool:
        """Validate if image format is supported."""
        if not mime_type:
            return False
        
        # Extract format from mime type
        format_part = mime_type.split('/')[-1].lower()
        return format_part in self.supported_formats


# Global instance
ocr_service = OCRService() 