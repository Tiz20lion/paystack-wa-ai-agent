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
        """Generate professional TizLion AI branded receipt using PIL"""
        try:
            # Create professional receipt with TizLion AI branding (higher resolution for better quality)
            img_width, img_height = 600, 900  # Increased resolution for sharper image
            img = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Enable anti-aliasing for smoother drawing
            # This will be applied to text and shapes for better quality
            
            # Define TizLion AI brand colors
            navy_blue = '#1e3a8a'
            cyan = '#06b6d4'
            light_blue = '#f0f9ff'
            gray = '#64748b'
            success_green = '#166534'
            success_bg = '#dcfce7'
            
            # Load and prepare TizLion AI logo for watermark
            logo_path = Path(__file__).parent / "assets" / "tizlionailogo.png"
            watermark_logo = None
            
            try:
                if logo_path.exists():
                    watermark_logo = Image.open(logo_path)
                    # Resize logo for watermark (scaled for higher resolution)
                    watermark_max_width = 400  # Scaled up for higher resolution
                    watermark_max_height = 320  # Scaled up for higher resolution
                    
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
                    
                    # Make watermark semi-transparent
                    watermark_alpha = Image.new('RGBA', watermark_logo.size, (0, 0, 0, 0))
                    watermark_alpha.paste(watermark_logo, (0, 0))
                    
                    # Apply transparency (25% opacity for better visibility with larger size)
                    for x in range(watermark_logo.width):
                        for y in range(watermark_logo.height):
                            pixel = watermark_logo.getpixel((x, y))
                            if len(pixel) == 4:  # RGBA
                                new_alpha = int(pixel[3] * 0.25)  # 25% opacity
                                watermark_logo.putpixel((x, y), (pixel[0], pixel[1], pixel[2], new_alpha))
                        
                    logger.debug(f"Watermark logo prepared: {new_width}x{new_height}")
                else:
                    logger.warning(f"Logo file not found at {logo_path}")
            except Exception as e:
                logger.warning(f"Could not load logo for watermark: {e}")
                watermark_logo = None
            
            # Load system fonts (cross-platform) with higher resolution sizes
            try:
                if sys.platform.startswith('win'):
                    font_brand = ImageFont.truetype("arial.ttf", 34)  # Scaled up for higher resolution
                    font_title = ImageFont.truetype("arial.ttf", 32)
                    font_large = ImageFont.truetype("arial.ttf", 52)
                    font_large_bold = ImageFont.truetype("arialbd.ttf", 52)  # Bold font for amount
                    font_medium = ImageFont.truetype("arial.ttf", 26)
                    font_small = ImageFont.truetype("arial.ttf", 20)
                    font_tiny = ImageFont.truetype("arial.ttf", 17)
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
                        font_brand = ImageFont.truetype(font_path, 34)
                        font_title = ImageFont.truetype(font_path, 32)
                        font_large = ImageFont.truetype(font_path, 52)
                        font_large_bold = ImageFont.truetype(font_path, 52)  # Bold font for amount
                        font_medium = ImageFont.truetype(font_path, 26)
                        font_small = ImageFont.truetype(font_path, 20)
                        font_tiny = ImageFont.truetype(font_path, 17)
                    else:
                        raise Exception("No suitable font found")
            except:
                # Fallback to default fonts
                font_brand = ImageFont.load_default()
                font_title = ImageFont.load_default()
                font_large = ImageFont.load_default()
                font_large_bold = ImageFont.load_default()  # Bold font for amount
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_tiny = ImageFont.load_default()
            
            # -- HEADER -- (scaled for higher resolution)
            header_height = 140  # Increased proportionally
            draw.rectangle([0, 0, img_width, header_height], fill=navy_blue)
            
            # Draw custom checkmark icon in center above title (based on SVG design)
            check_size = 28  # Scaled up for higher resolution
            check_x = (img_width - check_size) // 2
            check_y = 12  # Adjusted for higher resolution
            
            # Draw checkmark background circle (green circle like in SVG)
            circle_padding = 6  # Scaled up for higher resolution
            circle_x = check_x - circle_padding
            circle_y = check_y - circle_padding
            circle_size = check_size + (circle_padding * 2)
            
            # Draw green filled circle background (matching SVG #25AE88)
            svg_green = '#25AE88'
            draw.ellipse([circle_x, circle_y, circle_x + circle_size, circle_y + circle_size], 
                        fill=svg_green)
            
            # Draw white checkmark using polyline coordinates from SVG
            # SVG coordinates: (38,15) -> (22,33) -> (12,25) scaled to fit our circle
            # Scale factor: check_size / 50 (SVG viewBox) = 20/50 = 0.4
            scale = check_size / 50.0
            
            # Calculate checkmark points relative to circle center
            center_x = circle_x + circle_size // 2
            center_y = circle_y + circle_size // 2
            
            # SVG polyline points scaled and positioned
            point1_x = center_x + int((38 - 25) * scale)  # 38 relative to center (25)
            point1_y = center_y + int((15 - 25) * scale)  # 15 relative to center (25)
            
            point2_x = center_x + int((22 - 25) * scale)  # 22 relative to center (25)
            point2_y = center_y + int((33 - 25) * scale)  # 33 relative to center (25)
            
            point3_x = center_x + int((12 - 25) * scale)  # 12 relative to center (25)
            point3_y = center_y + int((25 - 25) * scale)  # 25 relative to center (25)
            
            # Draw white checkmark with proper thickness (scaled for higher resolution)
            check_thickness = 3  # Increased thickness for better visibility
            for i in range(check_thickness):
                # First line: from point3 to point2 (left part of checkmark)
                draw.line([point3_x, point3_y + i, point2_x, point2_y + i], 
                         fill='white', width=3)  # Increased line width
                # Second line: from point2 to point1 (right part of checkmark)
                draw.line([point2_x, point2_y + i, point1_x, point1_y + i], 
                         fill='white', width=3)  # Increased line width
            
            # "Transfer Success" title - centered below checkmark (adjusted for higher resolution)
            title_text = "Transfer Successful"
            title_font = font_title
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (img_width - title_width) // 2
            title_y = check_y + check_size + circle_padding + 12  # Adjusted spacing for higher resolution
            draw.text((title_x, title_y), title_text, fill='white', font=title_font)
            
            # Subtitle (adjusted positioning for higher resolution)
            subtitle_text = "Secure TizLion AI Banking Assistant"
            subtitle_font = font_tiny
            subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (img_width - subtitle_width) // 2
            subtitle_y = title_y + 36  # Increased spacing for higher resolution
            draw.text((subtitle_x, subtitle_y), subtitle_text, fill='#cbd5e1', font=subtitle_font)
            
            # Gradient bar under header (1–2px height)
            gradient_y = header_height
            gradient_height = 4
            for i in range(gradient_height):
                blend = i / gradient_height
                r = int(30 * (1 - blend) + 6 * blend)
                g = int(58 * (1 - blend) + 182 * blend)
                b = int(138 * (1 - blend) + 212 * blend)
                draw.line([(0, gradient_y + i), (img_width, gradient_y + i)], fill=(r, g, b))
            
            # Optional: Thin separator line below gradient
            draw.line([(0, gradient_y + gradient_height), (img_width, gradient_y + gradient_height)], fill='#e2e8f0', width=1)
            
            # Add watermark logo in the center background
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
            
            # Amount section with modern styling (scaled for higher resolution)
            amount_y = header_height + gradient_height + 15  # Adjusted spacing
            amount_height = 115  # Increased height for higher resolution
            draw.rectangle([30, amount_y, img_width - 30, amount_y + amount_height], 
                          fill=light_blue)  # Increased padding
            
            # Amount text (positioned for higher resolution)
            amount_text = f"₦{receipt_info['amount']:,.2f}"
            amount_bbox = draw.textbbox((0, 0), amount_text, font=font_large_bold)
            amount_width = amount_bbox[2] - amount_bbox[0]
            amount_x = (img_width - amount_width) // 2
            draw.text((amount_x, amount_y + 35), amount_text, fill=navy_blue, font=font_large_bold)  # Adjusted position
            
            # Amount label (positioned for higher resolution)
            amount_label = "AMOUNT"
            label_bbox = draw.textbbox((0, 0), amount_label, font=font_tiny)
            label_width = label_bbox[2] - label_bbox[0]
            label_x = (img_width - label_width) // 2
            draw.text((label_x, amount_y + 95), amount_label, fill=gray, font=font_tiny)  # Adjusted position
            
            # Details section (adjusted for higher resolution)
            details_y = amount_y + amount_height + 30  # Increased spacing
            details_padding = 45  # Increased padding for higher resolution
            
            # Transaction details
            details = [
                ("TO", receipt_info['recipient_name']),
                ("ACCOUNT", receipt_info['account_number']),
                ("BANK", receipt_info['bank_name']),
                ("STATUS", receipt_info['status'].upper()),
                ("DATE", receipt_info['timestamp']),
            ]
            
            for i, (label, value) in enumerate(details):
                y = details_y + (i * 55)  # Increased spacing between items
                
                # Draw separator line (adjusted for higher resolution)
                if i > 0:
                    draw.line([details_padding, y - 28, img_width - details_padding, y - 28], 
                             fill='#e2e8f0', width=2)  # Increased line width for better visibility
                
                # Label
                draw.text((details_padding, y), label, fill=gray, font=font_small)
                
                # Value
                if label == "STATUS":
                    # Enhanced status badge with better visibility (smaller size)
                    status_color = success_green if receipt_info['status'] == 'success' else '#991b1b'
                    status_bg_color = success_bg if receipt_info['status'] == 'success' else '#fee2e2'
                    
                    # Use small font but with better styling (scaled for higher resolution)
                    value_bbox = draw.textbbox((0, 0), value, font=font_small)
                    badge_width = value_bbox[2] - value_bbox[0] + 30  # Increased padding for higher resolution
                    badge_height = 32  # Increased height for higher resolution
                    badge_x = img_width - details_padding - badge_width
                    badge_y = y - 4  # Adjusted position
                    
                    # Draw enhanced status badge with rounded corners effect
                    draw.rectangle([badge_x, badge_y, badge_x + badge_width, badge_y + badge_height], 
                                 fill=status_bg_color, outline=status_color, width=2)
                    
                    # Add subtle shadow effect
                    draw.rectangle([badge_x + 1, badge_y + 1, badge_x + badge_width + 1, badge_y + badge_height + 1], 
                                 fill='#00000020', outline='#00000020', width=1)
                    
                    # Main badge
                    draw.rectangle([badge_x, badge_y, badge_x + badge_width, badge_y + badge_height], 
                                 fill=status_bg_color, outline=status_color, width=2)
                    
                    # Status text with better positioning (adjusted for higher resolution)
                    text_x = badge_x + 15  # Centered in badge with more padding
                    text_y = badge_y + 6   # Centered vertically with adjustment
                    draw.text((text_x, text_y), value, fill=status_color, font=font_small)
                else:
                    # Regular value - right aligned
                    value_bbox = draw.textbbox((0, 0), value, font=font_medium)
                    value_width = value_bbox[2] - value_bbox[0]
                    value_x = img_width - details_padding - value_width
                    draw.text((value_x, y), value, fill='#1e293b', font=font_medium)
            
            # Footer section (adjusted for higher resolution)
            footer_y = details_y + (len(details) * 55) + 45  # Adjusted spacing for higher resolution
            
            # Footer background
            draw.rectangle([0, footer_y, img_width, img_height], fill='#f8fafc')
            draw.line([0, footer_y, img_width, footer_y], fill='#e2e8f0', width=2)  # Increased line width
            
            # Reference code (adjusted for higher resolution)
            ref_text = f"REF: {receipt_info['reference']}"
            ref_bbox = draw.textbbox((0, 0), ref_text, font=font_tiny)
            ref_width = ref_bbox[2] - ref_bbox[0]
            ref_x = (img_width - ref_width) // 2
            
            # Reference background (scaled for higher resolution)
            draw.rectangle([ref_x - 15, footer_y + 30, ref_x + ref_width + 15, footer_y + 58], 
                          fill='#e2e8f0', outline='#cbd5e1', width=2)  # Increased padding and border
            draw.text((ref_x, footer_y + 36), ref_text, fill='#475569', font=font_tiny)  # Adjusted position
            
            # TizBot AI branding (adjusted for higher resolution)
            powered_text = "Powered by TizLion AI"
            powered_bbox = draw.textbbox((0, 0), powered_text, font=font_tiny)
            powered_width = powered_bbox[2] - powered_bbox[0]
            powered_x = (img_width - powered_width) // 2
            draw.text((powered_x, footer_y + 80), powered_text, fill=gray, font=font_tiny)  # Adjusted position
            
            # Save image with maximum quality (PNG for lossless compression)
            img.save(output_path, 'PNG', optimize=True)
            
            # Verify file creation
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                file_size = os.path.getsize(output_path)
                logger.debug(f"Receipt with enhanced watermark and new header design generated successfully: {file_size} bytes")
                return True
            else:
                logger.error("Receipt file was not created or is empty")
                return False
        
        except Exception as e:
            logger.error(f"❌ Professional receipt generation failed: {e}")
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