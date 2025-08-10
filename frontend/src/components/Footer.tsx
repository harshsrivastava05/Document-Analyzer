export default function Footer() {
  return (
    <footer className="border-t border-white/10 bg-[#0B0B10]">
      <div className="mx-auto max-w-7xl px-6 py-10 text-sm text-gray-400">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© {new Date().getFullYear()} DocAnalyzer. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <a className="hover:text-white" href="#">
              Privacy
            </a>
            <a className="hover:text-white" href="#">
              Terms
            </a>
            <a className="hover:text-white" href="#">
              Contact
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
