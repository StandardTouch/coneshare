import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authService } from "../services/authService";
import { isSafeUrl } from "../lib/utils";
import { BRAND_CONFIG } from "../lib/brandConfig";

const BrandingContext = createContext(null);

export function BrandingProvider({ children }) {
  const [branding, setBranding] = useState({
    brandName: BRAND_CONFIG.name,
    brandLogoUrl: BRAND_CONFIG.logo.fallback,
    brandWebsiteUrl: BRAND_CONFIG.links.website,
    termsUrl: BRAND_CONFIG.links.terms,
    privacyPolicyUrl: BRAND_CONFIG.links.privacy,
    esignEnabled: false,
  });
  const [isLoading, setIsLoading] = useState(true);

  const fetchBranding = useCallback(async () => {
    try {
      const data = await authService.getPublicSettings();
      const websiteUrl = data?.brand_website_url;
      const terms = data?.terms_url;
      const privacy = data?.privacy_policy_url;

      setBranding({
        brandName: data?.brand_name || BRAND_CONFIG.name,
        brandLogoUrl: data?.brand_logo_url || BRAND_CONFIG.logo.fallback,
        brandWebsiteUrl: (websiteUrl && isSafeUrl(websiteUrl)) ? websiteUrl : BRAND_CONFIG.links.website,
        termsUrl: (terms && isSafeUrl(terms)) ? terms : BRAND_CONFIG.links.terms,
        privacyPolicyUrl: (privacy && isSafeUrl(privacy)) ? privacy : BRAND_CONFIG.links.privacy,
        esignEnabled: data?.esign_enabled || false,
      });
    } catch (error) {
      console.error("Failed to fetch public settings/branding:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBranding();
  }, [fetchBranding]);

  useEffect(() => {
    const faviconElement = document.querySelector("link[rel~='icon']");
    if (faviconElement && branding.brandLogoUrl) {
      faviconElement.href = branding.brandLogoUrl;
    }
  }, [branding.brandLogoUrl]);

  const value = {
    ...branding,
    isLoading,
    refetchBranding: fetchBranding,
  };

  return (
    <BrandingContext.Provider value={value}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  const context = useContext(BrandingContext);
  if (context === null) {
    return {
      brandName: BRAND_CONFIG.name,
      brandLogoUrl: BRAND_CONFIG.logo.fallback,
      brandWebsiteUrl: BRAND_CONFIG.links.website,
      termsUrl: BRAND_CONFIG.links.terms,
      privacyPolicyUrl: BRAND_CONFIG.links.privacy,
      esignEnabled: false,
      isLoading: false,
      refetchBranding: async () => {},
    };
  }
  return context;
}
