import type { Metadata } from "next";
import AccountControl from "./components/account-control";
import "./globals.css";

export const metadata: Metadata = {
  title: "RubriCheck AI",
  description: "Human-in-the-loop handwritten exam evaluation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col"><AccountControl />{children}</body>
    </html>
  );
}
