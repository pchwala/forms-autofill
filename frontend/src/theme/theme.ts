import { createTheme, type Theme } from "@mui/material/styles";

const commonTypography = {
  fontFamily:
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  h1: { fontWeight: 700 },
  h2: { fontWeight: 600 },
  h3: { fontWeight: 600 },
  h4: { fontWeight: 500 },
  body1: { lineHeight: 1.7 },
};

export const darkTheme: Theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#1976d2" },
    background: {
      default: "#111418",
      paper: "#1a1f26",
    },
    text: {
      primary: "#e8eaed",
      secondary: "#9aa0a6",
    },
    divider: "rgba(255,255,255,0.08)",
  },
  typography: commonTypography,
  shape: { borderRadius: 6 },
  components: {
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500, fontSize: "0.78rem" },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: { backgroundImage: "none" },
      },
    },
  },
});
