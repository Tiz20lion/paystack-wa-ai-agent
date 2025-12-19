"""
Receipt Generator - Professional PIL-based receipt generation
Uses only Pillow (PIL) for creating TizLion AI branded transaction receipts
"""

import os
import sys
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import pytz

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from app.utils.logger import get_logger

logger = get_logger("receipt_generator")

class ReceiptGenerator:
    """Generate professional receipt images using PIL only"""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not PIL_AVAILABLE:
            logger.error("❌ PIL (Pillow) not available - cannot generate receipts")
            raise ImportError("PIL (Pillow) is required for receipt generation")
        
        # Set up West African Time timezone
        self.wat_timezone = pytz.timezone('Africa/Lagos')  # West African Time (UTC+1)
        
        logger.info("✅ PIL Receipt Generator initialized - TizLion AI branding enabled")
    
    def _format_wat_timestamp(self, timestamp_str: str = None) -> str:
        """
        Format timestamp to West African Time with AM/PM format
        
        Args:
            timestamp_str: Optional timestamp string, if None uses current time
            
        Returns:
            Formatted timestamp string in WAT with AM/PM (without seconds and WAT suffix)
        """
        try:
            if timestamp_str:
                # Parse the input timestamp (try different formats)
                dt = None
                
                # Try different timestamp formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',  # Standard format
                    '%Y-%m-%dT%H:%M:%S.%f',  # ISO format with microseconds
                    '%Y-%m-%dT%H:%M:%S',  # ISO format without microseconds
                    '%Y-%m-%d %H:%M:%S.%f',  # Standard format with microseconds
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(timestamp_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if dt is None:
                    # If none of the formats work, use current time
                    dt = datetime.now(self.wat_timezone)
                else:
                    # Localize to UTC first, then convert to WAT
                    dt = pytz.UTC.localize(dt).astimezone(self.wat_timezone)
            else:
                # Get current time in WAT
                dt = datetime.now(self.wat_timezone)
            
            # Format with AM/PM without seconds and WAT suffix
            return dt.strftime('%Y-%m-%d %I:%M %p')
        except Exception as e:
            logger.warning(f"Error formatting timestamp: {e}")
            # Fallback to current time in WAT
            dt = datetime.now(self.wat_timezone)
            return dt.strftime('%Y-%m-%d %I:%M %p')
    
    def generate_receipt_image(self, receipt_data: Dict) -> Optional[str]:
        """
        Generate a professional receipt image from transfer data
        
        Args:
            receipt_data: Dictionary containing transfer details
            
        Returns:
            Path to the generated image file, or None if generation failed
        """
        try:
            # Validate required data
            required_fields = ['amount', 'recipient_name', 'reference']
            missing_fields = [field for field in required_fields if field not in receipt_data]
            if missing_fields:
                logger.error(f"❌ Missing required fields in receipt data: {missing_fields}")
                logger.debug(f"Available fields: {list(receipt_data.keys())}")
                return None
            
            logger.info(f"📄 Generating PIL receipt for: {receipt_data.get('recipient_name')} - ₦{receipt_data.get('amount'):,.2f}")
            
            # Prepare receipt data
            receipt_info = {
                'amount': receipt_data.get('amount', 0),
                'recipient_name': receipt_data.get('recipient_name', 'Unknown'),
                'account_number': receipt_data.get('account_number', 'N/A'),
                'bank_name': receipt_data.get('bank_name', 'Unknown Bank'),
                'reference': receipt_data.get('reference', 'N/A'),
                'status': receipt_data.get('status', 'pending'),
                'timestamp': self._format_wat_timestamp(receipt_data.get('timestamp')),
                'generated_at': self._format_wat_timestamp()  # Current time in WAT
            }
            
            # Generate image filename (using PNG for higher quality)
            reference = receipt_data.get('reference', 'unknown')
            safe_reference = "".join(c for c in reference if c.isalnum() or c in ('-', '_'))
            image_filename = f"{safe_reference}.png"  # Changed to PNG for better quality
            image_path = self.output_dir / image_filename
            
            # Generate professional receipt
            if self._generate_professional_receipt(str(image_path), receipt_info):
                logger.info(f"✅ Professional TizLion AI receipt generated: {image_path}")
                return str(image_path)
            else:
                logger.error("❌ Receipt generation failed")
                return None
        
        except Exception as e:
            logger.error(f"❌ Error generating receipt image: {e}")
            logger.debug(f"Receipt data: {receipt_data}")
            return None
    
    def _generate_professional_receipt(self, output_path: str, receipt_info: Dict) -> bool:
        """Generate minimalist, high-quality TizLion AI branded receipt using PIL"""
        try:
            # Create portrait-sized receipt for mobile screens (Samsung S24 Ultra style)
            img_width, img_height = 1080, 1920  # Portrait size for mobile viewing
            img = Image.new('RGB', (img_width, img_height), color='#ffffff')
            draw = ImageDraw.Draw(img)
            
            # Minimalist color palette - subtle and elegant
            primary_dark = '#0f172a'  # Deep slate for primary text
            primary_light = '#1e293b'  # Lighter slate for secondary text
            accent_green = '#10b981'  # Modern success green
            accent_blue = '#3b82f6'  # Subtle blue accent
            text_muted = '#64748b'  # Muted gray for labels
            text_light = '#94a3b8'  # Light gray for subtle text
            border_color = '#e2e8f0'  # Very light border
            bg_subtle = '#f8fafc'  # Subtle background
            success_bg = '#ecfdf5'  # Very subtle success background
            
            # Load and prepare TizLion AI logo for watermark
            logo_path = Path(__file__).parent / "assets" / "tizlionailogo.png"
            watermark_logo = None
            
            try:
                if logo_path.exists():
                    watermark_logo = Image.open(logo_path)
                    # Resize logo for watermark (scaled for portrait size)
                    watermark_max_width = 800  # Scaled for portrait size
                    watermark_max_height = 640  # Scaled for portrait size
                    
                    # Calculate resize ratio maintaining aspect ratio
                    width_ratio = watermark_max_width / watermark_logo.width
                    height_ratio = watermark_max_height / watermark_logo.height
                    resize_ratio = min(width_ratio, height_ratio)
                    
                    new_width = int(watermark_logo.width * resize_ratio)
                    new_height = int(watermark_logo.height * resize_ratio)
                    
                    watermark_logo = watermark_logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Convert to RGBA for transparency
                    if watermark_logo.mode != 'RGBA':
                        watermark_logo = watermark_logo.convert('RGBA')
                    
                    # Make watermark 5% more visible (20% opacity)
                    for x in range(watermark_logo.width):
                        for y in range(watermark_logo.height):
                            pixel = watermark_logo.getpixel((x, y))
                            if len(pixel) == 4:  # RGBA
                                new_alpha = int(pixel[3] * 0.20)  # 20% opacity (5% more visible)
                                watermark_logo.putpixel((x, y), (pixel[0], pixel[1], pixel[2], new_alpha))
                        
                    logger.debug(f"Watermark logo prepared: {new_width}x{new_height}")
                else:
                    logger.warning(f"Logo file not found at {logo_path}")
            except Exception as e:
                logger.warning(f"Could not load logo for watermark: {e}")
                watermark_logo = None
            
            # Load system fonts with optimized sizes for minimalist design
            # Scaled for portrait size (1080x1920)
            try:
                if sys.platform.startswith('win'):
                    font_display = ImageFont.truetype("arial.ttf", 96)  # Large display font for amount (scaled)
                    font_display_bold = ImageFont.truetype("arialbd.ttf", 96)  # Bold for amount (scaled)
                    font_heading = ImageFont.truetype("arial.ttf", 36)  # Heading font (scaled)
                    font_detail = ImageFont.truetype("arial.ttf", 32)  # Consistent font for all details (scaled)
                    font_label = ImageFont.truetype("arial.ttf", 24)  # Labels (scaled)
                    font_caption = ImageFont.truetype("arial.ttf", 20)  # Caption/small text (scaled)
                    font_tiny = ImageFont.truetype("arial.ttf", 18)  # Very small text (scaled)
                else:
                    # Linux/macOS font paths
                    font_paths = [
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                        "/System/Library/Fonts/Arial.ttf",  # macOS
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    ]
                    
                    font_path = None
                    for font in font_paths:
                        if os.path.exists(font):
                            font_path = font
                            break
                    
                    if font_path:
                        font_display = ImageFont.truetype(font_path, 96)
                        font_display_bold = ImageFont.truetype(font_path, 96)
                        font_heading = ImageFont.truetype(font_path, 36)
                        font_detail = ImageFont.truetype(font_path, 32)
                        font_label = ImageFont.truetype(font_path, 24)
                        font_caption = ImageFont.truetype(font_path, 20)
                        font_tiny = ImageFont.truetype(font_path, 18)
                    else:
                        raise Exception("No suitable font found")
            except:
                # Fallback to default fonts
                font_display = ImageFont.load_default()
                font_display_bold = ImageFont.load_default()
                font_heading = ImageFont.load_default()
                font_detail = ImageFont.load_default()
                font_label = ImageFont.load_default()
                font_caption = ImageFont.load_default()
                font_tiny = ImageFont.load_default()
            
            # -- MINIMALIST HEADER -- Clean and spacious (scaled for portrait)
            top_padding = 120  # Scaled for portrait size
            current_y = top_padding
            
            # Load and display success checkmark icon from checked.png
            check_icon_path = Path(__file__).parent / "assets" / "checked.png"
            check_icon = None
            check_icon_size = 120  # Scaled for portrait size
            
            try:
                if check_icon_path.exists():
                    check_icon = Image.open(check_icon_path)
                    # Resize icon maintaining aspect ratio
                    original_width, original_height = check_icon.size
                    aspect_ratio = original_width / original_height
                    
                    if aspect_ratio >= 1:
                        # Width is larger or equal
                        new_width = check_icon_size
                        new_height = int(check_icon_size / aspect_ratio)
                    else:
                        # Height is larger
                        new_height = check_icon_size
                        new_width = int(check_icon_size * aspect_ratio)
                    
                    check_icon = check_icon.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Convert to RGBA if needed for transparency
                    if check_icon.mode != 'RGBA':
                        check_icon = check_icon.convert('RGBA')
                    
                    # Calculate position (centered)
                    check_x = (img_width - new_width) // 2
                    check_y = current_y
                    
                    # Paste the checkmark icon onto the image
                    img.paste(check_icon, (check_x, check_y), check_icon)
                    
                    # Update current_y based on icon height
                    current_y = check_y + new_height + 48  # Scaled spacing after icon
                    logger.debug(f"Success icon loaded: {new_width}x{new_height}")
                else:
                    logger.warning(f"Checked icon not found at {check_icon_path}, using fallback")
                    # Fallback: use a simple circle if icon not found
                    check_size = 72
                    circle_size = check_size + 24
                    circle_x = (img_width - circle_size) // 2
                    circle_y = current_y
                    draw.ellipse([circle_x, circle_y, circle_x + circle_size, circle_y + circle_size], 
                                fill=success_bg, outline=accent_green, width=2)
                    current_y = circle_y + circle_size + 48
            except Exception as e:
                logger.warning(f"Could not load success icon: {e}, using fallback")
                # Fallback: use a simple circle if icon loading fails
                check_size = 72
                circle_size = check_size + 24
                circle_x = (img_width - circle_size) // 2
                circle_y = current_y
                draw.ellipse([circle_x, circle_y, circle_x + circle_size, circle_y + circle_size], 
                            fill=success_bg, outline=accent_green, width=2)
                current_y = circle_y + circle_size + 48
            
            # Title - minimalist typography (scaled spacing)
            title_text = "Transfer Successful"
            title_bbox = draw.textbbox((0, 0), title_text, font=font_heading)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (img_width - title_width) // 2
            draw.text((title_x, current_y), title_text, fill=primary_dark, font=font_heading)
            
            # Subtle subtitle (scaled spacing)
            current_y += 60  # Scaled
            subtitle_text = "TizLion AI Banking"
            subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=font_caption)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (img_width - subtitle_width) // 2
            draw.text((subtitle_x, current_y), subtitle_text, fill=text_muted, font=font_caption)
            
            # Subtle divider line (scaled)
            current_y += 90  # Scaled
            draw.line([100, current_y, img_width - 100, current_y], fill=border_color, width=2)  # Scaled
            
            # -- AMOUNT SECTION -- Minimalist and prominent (scaled spacing)
            current_y += 80  # Scaled
            amount_text = f"₦{receipt_info['amount']:,.2f}"
            amount_bbox = draw.textbbox((0, 0), amount_text, font=font_display_bold)
            amount_width = amount_bbox[2] - amount_bbox[0]
            amount_x = (img_width - amount_width) // 2
            draw.text((amount_x, current_y), amount_text, fill=primary_dark, font=font_display_bold)
            
            # Amount label - subtle (scaled spacing)
            current_y += 120  # Scaled
            amount_label = "Amount Transferred"
            label_bbox = draw.textbbox((0, 0), amount_label, font=font_caption)
            label_width = label_bbox[2] - label_bbox[0]
            label_x = (img_width - label_width) // 2
            draw.text((label_x, current_y), amount_label, fill=text_muted, font=font_caption)
            
            # Subtle divider (scaled)
            current_y += 100  # Scaled
            draw.line([100, current_y, img_width - 100, current_y], fill=border_color, width=2)  # Scaled
            
            # Add watermark logo in the center background (before details)
            if watermark_logo:
                # Calculate watermark position (center of receipt)
                watermark_x = (img_width - watermark_logo.width) // 2
                watermark_y = (img_height - watermark_logo.height) // 2
                
                # Create a temporary image for watermark overlay
                watermark_layer = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
                watermark_layer.paste(watermark_logo, (watermark_x, watermark_y), watermark_logo)
                
                # Convert main image to RGBA for blending
                img_rgba = img.convert('RGBA')
                # Blend watermark with main image
                img_with_watermark = Image.alpha_composite(img_rgba, watermark_layer)
                # Convert back to RGB
                img = img_with_watermark.convert('RGB')
                # Recreate draw object for the new image
                draw = ImageDraw.Draw(img)
            
            # -- TRANSACTION DETAILS -- Clean list format with consistent font size
            current_y += 80  # Increased spacing for portrait size
            details_padding = 100  # Increased padding for portrait size
            
            # Transaction details with minimalist layout - all same font size
            details = [
                ("Recipient", receipt_info['recipient_name']),
                ("Account", receipt_info['account_number']),
                ("Bank", receipt_info['bank_name']),
                ("Date", receipt_info['timestamp']),
                ("Reference", receipt_info['reference']),
            ]
            
            # Consistent spacing between items (scaled for portrait)
            detail_spacing = 90
            
            for i, (label, value) in enumerate(details):
                y = current_y + (i * detail_spacing)  # Consistent spacing
                
                # Subtle separator line
                if i > 0:
                    separator_y = y - (detail_spacing // 2)
                    draw.line([details_padding, separator_y, img_width - details_padding, separator_y], 
                             fill=border_color, width=1)
                
                # Label - left aligned, muted, same font size as value
                draw.text((details_padding, y), label, fill=text_muted, font=font_detail)
                
                # Value - right aligned, same font size as label
                value_bbox = draw.textbbox((0, 0), value, font=font_detail)
                value_width = value_bbox[2] - value_bbox[0]
                value_x = img_width - details_padding - value_width
                draw.text((value_x, y), value, fill=primary_dark, font=font_detail)
            
            # -- FOOTER -- Minimalist and clean
            footer_y = current_y + (len(details) * detail_spacing) + 80
            
            # Subtle top border
            draw.line([0, footer_y, img_width, footer_y], fill=border_color, width=1)
            
            # Branding - very subtle
            branding_y = img_height - 60
            powered_text = "TizLion AI"
            powered_bbox = draw.textbbox((0, 0), powered_text, font=font_tiny)
            powered_width = powered_bbox[2] - powered_bbox[0]
            powered_x = (img_width - powered_width) // 2
            draw.text((powered_x, branding_y), powered_text, fill=text_light, font=font_tiny)
            
            # Save image with maximum quality (PNG for lossless compression)
            # Note: compress_level=1 provides fast compression with good quality
            # Using optimize=True would override compress_level to 9 (maximum compression)
            img.save(output_path, 'PNG', compress_level=1)
            
            # Verify file creation
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                file_size = os.path.getsize(output_path)
                logger.debug(f"Minimalist high-quality receipt generated successfully: {file_size} bytes")
                return True
            else:
                logger.error("Receipt file was not created or is empty")
                return False
        
        except Exception as e:
            logger.error(f"❌ Minimalist receipt generation failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def cleanup_old_receipts(self, max_age_hours: int = 24):
        """Clean up old receipt files"""
        try:
            current_time = datetime.now()
            
            # Clean up both PNG and JPG files for backward compatibility
            for pattern in ["*.png", "*.jpg"]:
                for receipt_file in self.output_dir.glob(pattern):
                    file_age = current_time - datetime.fromtimestamp(receipt_file.stat().st_mtime)
                    
                    if file_age.total_seconds() > (max_age_hours * 3600):
                        receipt_file.unlink()
                        logger.debug(f"Cleaned up old receipt: {receipt_file}")
        
        except Exception as e:
            logger.error(f"Error during receipt cleanup: {e}")

def generate_receipt_image(receipt_data: Dict) -> Optional[str]:
    """
    Convenience function to generate a receipt image using PIL only
    
    Args:
        receipt_data: Dictionary containing transfer details
        
    Returns:
        Path to the generated image file, or None if generation failed
    """
    generator = ReceiptGenerator()
    return generator.generate_receipt_image(receipt_data) 