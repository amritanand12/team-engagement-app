import React, { useEffect, useRef } from 'react';
import { Sparkles, Heart, Gift, Star, Users, Zap, Award } from 'lucide-react';

export const EngagementMotionGraphic: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const mouse = { x: -1000, y: -1000, radius: 140 };

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };

    const handleMouseLeave = () => {
      mouse.x = -1000;
      mouse.y = -1000;
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    // Dynamic celebration constellation particles
    const particleCount = Math.min(Math.floor((width * height) / 22000), 55);
    const particles: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      radius: number;
      color: string;
      baseAlpha: number;
      alpha: number;
    }> = [];

    const colors = [
      '#f43f5e', // rose-500
      '#ec4899', // pink-500
      '#a855f7', // purple-500
      '#6366f1', // indigo-500
      '#f59e0b', // amber-500
      '#38bdf8', // sky-400
    ];

    for (let i = 0; i < particleCount; i++) {
      const baseAlpha = Math.random() * 0.4 + 0.2;
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 2.2 + 1.2,
        color: colors[Math.floor(Math.random() * colors.length)],
        baseAlpha,
        alpha: baseAlpha,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Connect close nodes with subtle glowing celebration threads
      const maxDistance = 140;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < maxDistance) {
            const lineAlpha = (1 - dist / maxDistance) * 0.12;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(244, 63, 94, ${lineAlpha})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }

      // Update and render floating celebration sparks
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        // Interactive mouse proximity reaction
        const mdx = mouse.x - p.x;
        const mdy = mouse.y - p.y;
        const mdist = Math.sqrt(mdx * mdx + mdy * mdy);
        if (mdist < mouse.radius) {
          p.alpha = Math.min(1, p.baseAlpha + (1 - mdist / mouse.radius) * 0.5);
        } else {
          p.alpha = p.baseAlpha;
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha;
        ctx.shadowBlur = 12;
        ctx.shadowColor = p.color;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <>
      {/* Full-Screen Interactive Canvas */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0 pointer-events-none z-0"
      />

      {/* Floating Organic Milestone Celebrations (Background Ambience on Desktop) */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none">
        
        {/* Milestone Card: Sarah Chen 5-Year Anniversary (Top-Left Anchor) */}
        <div className="hidden lg:flex absolute top-12 left-10 xl:left-20 2xl:left-28 animate-float-slow pointer-events-auto">
          <div className="bg-slate-900/60 hover:bg-slate-900/80 backdrop-blur-xl border border-rose-500/25 hover:border-rose-500/40 rounded-2xl p-4 shadow-2xl shadow-rose-950/40 max-w-xs transition-all duration-300 group cursor-default">
            <div className="flex items-center gap-3">
              <div className="relative">
                <img
                  src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop&crop=face"
                  alt="Sarah Chen"
                  className="w-10 h-10 rounded-xl object-cover ring-2 ring-rose-400/40 shadow-sm"
                />
                <div className="absolute -bottom-1 -right-1 p-0.5 bg-rose-500 rounded-full text-white">
                  <Star className="w-2.5 h-2.5 fill-current text-amber-200" />
                </div>
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-white font-bold text-xs">Sarah Chen</span>
                  <span className="px-1.5 py-0.5 rounded-full text-[9px] font-extrabold uppercase bg-rose-500/20 text-rose-300 border border-rose-500/30">
                    5 Years
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">Engineering Lead</p>
              </div>
            </div>
            <p className="mt-2 text-[11px] text-slate-300 bg-slate-950/40 rounded-lg p-2 border border-slate-800/60 leading-relaxed">
              "Happy 5th Work Anniversary! 🥂 Thank you for your leadership."
            </p>
            <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
              <span className="flex items-center gap-1 text-rose-300">
                <Heart className="w-3 h-3 fill-rose-400 text-rose-400" />
                18 team cheers
              </span>
              <span className="text-emerald-400 font-medium">Delivered Today</span>
            </div>
          </div>
        </div>

        {/* Milestone Card: Liam Rivera Birthday (Bottom-Right Anchor) */}
        <div className="hidden lg:flex absolute bottom-12 right-10 xl:right-20 2xl:right-28 animate-float-reverse pointer-events-auto">
          <div className="bg-slate-900/60 hover:bg-slate-900/80 backdrop-blur-xl border border-indigo-500/25 hover:border-indigo-500/40 rounded-2xl p-4 shadow-2xl shadow-indigo-950/40 max-w-xs transition-all duration-300 group cursor-default">
            <div className="flex items-center gap-3">
              <div className="relative">
                <img
                  src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face"
                  alt="Liam Rivera"
                  className="w-10 h-10 rounded-xl object-cover ring-2 ring-indigo-400/40 shadow-sm"
                />
                <div className="absolute -bottom-1 -right-1 p-0.5 bg-indigo-500 rounded-full text-white">
                  <Gift className="w-2.5 h-2.5 text-amber-200" />
                </div>
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-white font-bold text-xs">Liam Rivera</span>
                  <span className="px-1.5 py-0.5 rounded-full text-[9px] font-extrabold uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    Birthday Today! 🎂
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">UX Design Ops</p>
              </div>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-400 bg-slate-950/40 rounded-lg p-2 border border-slate-800/60">
              <span className="flex items-center gap-1.5 text-indigo-300 text-[10px]">
                <Sparkles className="w-3 h-3 text-amber-400" />
                Festive Card & Coffee Gift Card
              </span>
              <span className="text-emerald-400 text-[10px] font-medium">Delivered</span>
            </div>
          </div>
        </div>

        {/* Live Milestone Pulse Pill (Bottom-Left Anchor) */}
        <div className="hidden xl:flex absolute bottom-12 left-10 xl:left-20 animate-float-subtle pointer-events-auto">
          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800/70 rounded-full px-4 py-2 flex items-center gap-3 shadow-xl">
            <div className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </div>
            <span className="text-xs text-slate-300 font-medium">
              Daily Celebration Pipeline: <strong className="text-rose-400">99.8%</strong> on-time delivery
            </span>
          </div>
        </div>

        {/* Feature Highlight Pill (Top-Right Anchor) */}
        <div className="hidden xl:flex absolute top-12 right-10 xl:right-20 animate-float-subtle pointer-events-auto">
          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800/70 rounded-full px-4 py-2 flex items-center gap-2 shadow-xl text-xs text-slate-300 font-medium">
            <Sparkles className="w-3.5 h-3.5 text-rose-400" />
            <span>Automated Culture & Milestone Platform</span>
          </div>
        </div>
      </div>
    </>
  );
};
