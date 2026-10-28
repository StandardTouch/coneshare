/**
 * Allure Clinic Brand Configuration
 * 
 * Centralized brand defaults for the Allure Clinic deployment.
 * These values are used as fallbacks when branding is not configured
 * through Admin → Branding.
 */

export const BRAND_CONFIG = {
  // Brand name (English and Arabic)
  name: 'Allure Clinic',
  nameArabic: 'ألور',
  
  // Logo paths (relative to /public)
  logo: {
    mark: '/brand/logo.svg',           // Teal mark only
    full: '/brand/logo-full.png',      // Full logo with wordmark
    fallback: '/brand/logo.svg',       // Default fallback
  },
  
  // Brand colors (from logo analysis)
  colors: {
    // Light teal accent (DO NOT use for text on white - insufficient contrast)
    tealLight: '#2BD3C8',
    
    // Darker teal for primary buttons (AA compliant, 5.05:1 on white)
    tealPrimary: '#0D7C75',
    
    // Slate grey for text (5.8:1 on white)
    slateGrey: '#5B6770',
  },
  
  // External links
  links: {
    website: 'https://allureclinic.com',
    /** Same-origin legal pages (see /terms and /privacy routes) */
    terms: '/terms',
    privacy: '/privacy',
  },

  /** Shown on Terms & Privacy pages; override in content or Admin contact fields if added later */
  /** Match Google OAuth "User support email" where possible */
  contactEmail: 'share@allureclinics.net',
  
  // Page metadata
  meta: {
    title: 'Allure Clinic | Secure Document Sharing',
    description: 'Secure document sharing and file management for Allure Clinic',
  },
};
