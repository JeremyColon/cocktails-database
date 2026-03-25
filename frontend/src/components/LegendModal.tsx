import { GlassWater, Hourglass, Frown, Droplet, Leaf, Star, Bookmark, ExternalLink, HelpCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const Row = ({ icon, description }: { icon: React.ReactNode; description: string }) => (
  <div className="flex items-center gap-2">
    <div className="w-5 flex items-center justify-center shrink-0">{icon}</div>
    <span className="font-body text-xs text-bark">{description}</span>
  </div>
)

export default function LegendPopover() {
  const { user } = useAuth()

  return (
    <div className="relative group">
      <button className="p-2 text-bark hover:text-mahogany transition-colors" aria-label="How it works">
        <HelpCircle className="w-5 h-5" />
      </button>

      {/* Popover */}
      <div className="absolute right-0 top-full mt-1 w-72 bg-white border border-parchment-300 rounded-xl shadow-card
                      opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto
                      transition-opacity duration-150 z-50">
        <div className="px-4 py-3 flex flex-col gap-3">

          <div>
            <p className="text-xs font-semibold text-bark uppercase tracking-wider mb-1.5">Availability</p>
            <div className="space-y-1.5">
              <Row icon={<GlassWater className="w-3.5 h-3.5 text-green-600" />} description="You can make this cocktail" />
              <Row icon={<Hourglass className="w-3.5 h-3.5 text-amber" />} description="You have some ingredients" />
              <Row icon={<Frown className="w-3.5 h-3.5 text-bark" />} description="Missing all ingredients" />
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-bark uppercase tracking-wider mb-1.5">Ingredients</p>
            <div className="space-y-1.5">
              <Row icon={<Droplet className="w-3 h-3 text-bark" />} description="Mixed into the drink" />
              <Row icon={<Leaf className="w-3 h-3 text-bark" />} description="Garnish only" />
              <Row
                icon={<span className="flex"><Droplet className="w-3 h-3 text-bark" /><Leaf className="w-3 h-3 text-bark -ml-0.5" /></span>}
                description="Both (e.g. mint in a julep)"
              />
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-bark uppercase tracking-wider mb-1.5">Actions</p>
            <div className="space-y-1.5">
              <Row icon={<Star className="w-3.5 h-3.5 text-amber" />} description="Favorite — filterable" />
              <Row icon={<Bookmark className="w-3.5 h-3.5 text-amber" />} description="Bookmark — filterable" />
              <Row icon={<span className="font-body text-xs font-semibold text-amber">8/10</span>} description="Your personal rating (0–10)" />
              <Row icon={<ExternalLink className="w-3.5 h-3.5 text-bark" />} description="View original recipe" />
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-bark uppercase tracking-wider mb-1.5">Ratings</p>
            <p className="font-body text-xs text-bark"><span className="font-semibold text-mahogany">NPS</span> — net promoter score. Positive means more people love it than dislike it.</p>
            {user && <p className="font-body text-xs text-bark mt-1">The amber bar on each card shows what % of ingredients you have.</p>}
          </div>

        </div>
      </div>
    </div>
  )
}
