import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "vietnamese"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://trondeonline.me"),
  title: {
    default: "ExamShuffling - Trộn đề thi trắc nghiệm tự động | Miễn phí",
    template: "%s | ExamShuffling",
  },
  description:
    "Trộn đề thi trắc nghiệm online miễn phí, nhanh chóng và chính xác. Hỗ trợ đảo câu hỏi, đảo đáp án, xuất file Word đẹp mắt. Công cụ đắc lực cho giáo viên.",
  keywords: [
    "trộn đề thi",
    "đảo đề thi",
    "trắc nghiệm online",
    "exam shuffling",
    "tạo đề kiểm tra",
    "công cụ giáo viên",
    "trondeonline",
    "trộn đề online",
    "đảo câu hỏi",
    "đảo đáp án",
    "xuất file word",
  ],
  authors: [{ name: "David Khanh" }],
  creator: "ExamShuffling Team",
  openGraph: {
    type: "website",
    locale: "vi_VN",
    url: "https://trondeonline.me",
    siteName: "ExamShuffling",
    title: "ExamShuffling - Trộn đề thi trắc nghiệm tự động",
    description:
      "Hệ thống trộn đề thi trắc nghiệm online miễn phí. Giúp giáo viên tạo nhiều mã đề từ ngân hàng câu hỏi chỉ trong vài giây.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "ExamShuffling - Trộn đề thi trắc nghiệm",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "ExamShuffling - Trộn đề thi trắc nghiệm tự động",
    description:
      "Hệ thống trộn đề thi trắc nghiệm online miễn phí. Giúp giáo viên tạo nhiều mã đề từ ngân hàng câu hỏi chỉ trong vài giây.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  alternates: {
    canonical: "https://trondeonline.me",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className="scroll-smooth">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
