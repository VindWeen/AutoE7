"""Conservative observations of English Rookie Arena, normalized RGB 1280x720.

No actions occur here. Unknown numbers remain None and never authorize spending.
"""
from pathlib import Path
import hashlib

import cv2
import numpy as np


class RookieArenaVision:
    def __init__(self, root):
        folder = Path(root) / 'assets' / 'rookie_arena'
        self.templates = {}
        self.digits = []
        self.flag_digits = []
        self._roster = None
        self._signature = None
        self._auto_samples = []
        for path in folder.glob('*.png'):
            im = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if path.stem.startswith('flagdigit_'):
                digit=int(path.stem.split('_')[1])
                for threshold in (110,135,160,185):
                    mask=(im>threshold).astype(np.uint8)*255
                    ys,xs=np.nonzero(mask)
                    if len(xs):
                        self.flag_digits.append((digit,mask[ys.min():ys.max()+1,xs.min():xs.max()+1]))
            elif path.stem.startswith('digit_'):
                self.digits.append((int(path.stem.split('_')[1]), im))
            else:
                self.templates[path.stem] = im
        if {digit for digit,_ in self.flag_digits} != set(range(10)):
            raise ValueError('Missing Rookie Arena flags digit templates')
        required = ('title', 'opponents', 'list_prompt', 'team', 'start', 'battle', 'auto_off', 'auto_check',
                    'victory', 'defeat', 'purchase', 'friendship', 'cooldown', 'confirm',
                    'promotion_confirm', 'promotion_marker', 'promotion_rewards', 'promotion_close')
        required += ('friendship_level_title', 'friendship_level_close', 'flags_denominator')
        required += ('refresh_title', 'refresh_question', 'refresh_free_notice',
                     'refresh_free_cost', 'refresh_confirm', 'refresh_daily', 'refresh_remaining')
        required += ('skill_cannot_use',)
        required += ('auto_dead_label',)
        if any(name not in self.templates for name in required):
            raise ValueError('Missing Rookie Arena templates')

    def _match(self, gray, name, box, threshold=.80, brightness_floor=70):
        x1,y1,x2,y2 = box
        region = gray[y1:y2,x1:x2]
        template = self.templates[name]
        best = 0.
        for scale in (.98, 1., 1.02):
            t = cv2.resize(template, None, fx=scale, fy=scale)
            if t.shape[0]>region.shape[0] or t.shape[1]>region.shape[1]:
                continue
            _,score,_,(x,y) = cv2.minMaxLoc(cv2.matchTemplate(region,t,cv2.TM_CCOEFF_NORMED))
            patch=region[y:y+t.shape[0],x:x+t.shape[1]]
            # Correlation alone also matches a dimmed background under a modal.
            mask=t>float(t.max())*.8
            if np.any(mask) and patch[mask].mean() > max(brightness_floor,float(t.max())*.52):
                best=max(best,score)
        return best>=threshold

    @staticmethod
    def _mask(rgb, green=False):
        r,g,b = [rgb[:,:,i].astype(float) for i in range(3)]
        if green:
            return ((g>110)&(g>r*1.3)&(g>b*1.3)).astype(np.uint8)*255
        return ((np.minimum(np.minimum(r,g),b)>150)&
                ((np.maximum(np.maximum(r,g),b)-np.minimum(np.minimum(r,g),b))<65)).astype(np.uint8)*255

    def _number(self, rgb, green=False, owned=False):
        mask=self._mask(rgb,green)
        _,_,stats,_=cv2.connectedComponentsWithStats(mask)
        boxes=sorted([(x,y,w,h) for x,y,w,h,a in stats[1:] if h>=11 and w>=2],key=lambda b:b[0])
        if owned:
            # The gap after 'Owned:' separates its letters from the digit run.
            breaks=[i for i in range(1,len(boxes)) if boxes[i][0]-(boxes[i-1][0]+boxes[i-1][2])>=6]
            if not breaks:
                return None
            boxes=boxes[breaks[-1]:]
        if not boxes or len(boxes)>6:
            return None
        digits=[]
        for x,y,w,h in boxes:
            glyph=mask[y:y+h,x:x+w]
            # Compare both masks on a common, larger grid. Nearest-neighbour
            # reduction into a small reference discards strokes when the game
            # window is resized by even a pixel (notably the tail of 9).
            normalized=cv2.resize(glyph,(24,32),interpolation=cv2.INTER_LINEAR).astype(float)/255
            scores={}
            for digit,t in self.digits:
                target=cv2.resize(t,(24,32),interpolation=cv2.INTER_LINEAR).astype(float)/255
                score=np.minimum(normalized,target).sum()/max(1,np.maximum(normalized,target).sum())
                score-=abs(w/h-t.shape[1]/t.shape[0])*.35
                scores[digit]=max(scores.get(digit,0),score)
            ranked=sorted(scores.items(),key=lambda item:item[1],reverse=True)
            if not ranked or ranked[0][1]<.66 or (len(ranked)>1 and ranked[0][1]-ranked[1][1]<.055):
                return None
            digits.append(str(ranked[0][0]))
        return int(''.join(digits))

    def _flags(self, rgb):
        """Read the white numerator without discarding disconnected strokes.

        Header glyphs can split into several components after client resizing.
        Column projection keeps all strokes sharing a digit's horizontal span.
        Multiple brightness cuts must agree; currency OCR remains independent.
        """
        lo=rgb.min(axis=2).astype(float)
        chroma=rgb.max(axis=2).astype(float)-lo
        votes=[]
        for threshold in (110, 135, 160, 185):
            mask=((lo>threshold)&(chroma<65)).astype(np.uint8)*255
            occupied=np.any(mask,axis=0)
            edges=np.diff(np.r_[False,occupied,False].astype(int))
            spans=list(zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))
            glyphs=[]
            for left,right in spans:
                ys=np.flatnonzero(np.any(mask[:,left:right],axis=1))
                if len(ys) and ys[-1]-ys[0]+1>=11 and right-left>=2:
                    glyphs.append(mask[ys[0]:ys[-1]+1,left:right])
            if not glyphs or len(glyphs)>2:
                continue
            digits=[]
            for glyph in glyphs:
                h,w=glyph.shape
                normalized=cv2.resize(glyph,(24,32),interpolation=cv2.INTER_LINEAR).astype(float)/255
                scores={}
                for digit,template in self.digits+self.flag_digits:
                    if abs(w/h-template.shape[1]/template.shape[0])>.10:
                        continue
                    target=cv2.resize(template,(24,32),interpolation=cv2.INTER_LINEAR).astype(float)/255
                    score=np.minimum(normalized,target).sum()/max(1,np.maximum(normalized,target).sum())
                    score-=abs(w/h-template.shape[1]/template.shape[0])*.35
                    scores[digit]=max(scores.get(digit,0),score)
                ranked=sorted(scores.items(),key=lambda item:item[1],reverse=True)
                if not ranked or ranked[0][1]<.66 or (len(ranked)>1 and ranked[0][1]-ranked[1][1]<.055):
                    break
                digits.append(str(ranked[0][0]))
            if len(digits)==len(glyphs):
                votes.append(int(''.join(digits)))
        # Never resolve contradictory confident readings by majority vote.
        return votes[0] if len(votes)>=2 and len(set(votes))==1 else None

    def _manual_slot(self, rgb, gray, x):
        skill=rgb[617:715,x:x+90].astype(float)
        r,g,b=skill.transpose(2,0,1)
        gold=(r>105)&(g>80)&(r>b*1.2)&(g>b*1.05)
        # Inspect the frame edges, not a particular hero's skill art.
        rim=np.r_[gold[:12].ravel(),gold[-12:].ravel(),
                  gold[12:-12,:12].ravel(),gold[12:-12,-12:].ravel()]
        gold_frame=(gold[:12].mean()>.10 and
                    gold[:,:12].mean()>.15 and rim.mean()>.09)
        # Skills also have silver/blue frames (for example Landy).
        # Require a bright, contrasting perimeter on all three slots;
        # the interior's dominant skill-art colour is irrelevant.
        light=(np.maximum(np.maximum(r,g),b)>105)&(np.minimum(np.minimum(r,g),b)>40)
        light_rim=np.r_[light[:12].ravel(),light[-12:].ravel(),
                        light[12:-12,:12].ravel(),light[12:-12,-12:].ravel()]
        edge=cv2.Canny(gray[617:715,x:x+90],50,110)>0
        silver_frame=(light[:12].mean()>.15 and
                      light[:,:12].mean()>.15 and light_rim.mean()>.13 and
                      edge[:12].mean()>.06 and edge[:,:12].mean()>.06 and
                      edge[:12,20:70].sum(axis=1).max()>20)
        # A locked skill is dim and loses the bright frame. Its
        # explicit "Cannot use" label still proves a manual skill slot.
        disabled=self._match(gray,'skill_cannot_use',(x,630,min(1280,x+90),705),.82,
                             brightness_floor=45)
        return bool(gold_frame or silver_frame or disabled)

    def observe(self, frame, now=None):
        result=self._observe_frame(frame)
        if result['screen'] != 'battle':
            self._auto_samples.clear()
            return result
        # A timestamp is mandatory for temporal evidence. Standalone image
        # inspection must never interpret different fixtures as an animation.
        if now is None:
            self._auto_samples.clear()
            if result['auto_on'] is not None:
                result['auto_source']='hud'
            return result
        temporal=self._auto_icon_state(np.asarray(frame),now)
        if result['auto_on'] is None and temporal is not None:
            result['auto_on']=temporal
            result['auto_source']='icon_sequence'
        elif result['auto_on'] is not None:
            result['auto_source']='hud'
        return result

    def _auto_icon_state(self, rgb, now):
        """Observe the fixed A and rotating white arrows, never scene motion.

        A single idle-looking frame cannot authorize a toggle. Sample over
        real time; gaps, hidden icons and a new screen discard old evidence.
        """
        if self._auto_samples and (now < self._auto_samples[-1][0]
                                  or now-self._auto_samples[-1][0] > 1):
            self._auto_samples.clear()
        if self._auto_samples and now-self._auto_samples[-1][0] < .2:
            return None
        patch=rgb[9:58,1100:1150]
        white=(patch.min(axis=2)>175)&((patch.max(axis=2).astype(float)-patch.min(axis=2))<65)
        yy,xx=np.ogrid[:49,:50]
        radius=(xx-24)**2+(yy-24)**2
        ring=white & (radius>=12**2) & (radius<=24**2)
        center=white & (radius<10**2)
        if ring.sum()<40 or center.sum()<15:
            self._auto_samples.clear()
            return None
        gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
        idle=self._match(gray,'auto_off',(1090,0,1160,70),.94)
        self._auto_samples.append((now,ring,idle))
        self._auto_samples=[s for s in self._auto_samples if now-s[0]<=3]
        samples=self._auto_samples
        if len(samples)<6 or now-samples[0][0]<2:
            return None
        differences=[np.logical_xor(a[1],b[1]).sum()/max(1,np.logical_or(a[1],b[1]).sum())
                     for a,b in zip(samples,samples[1:])]
        # Require the reference idle pose throughout a quiet sequence. An
        # active icon passing its idle angle only once remains unknown.
        if all(s[2] for s in samples) and max(differences)<.18:
            return False
        if sum(not s[2] for s in samples)>=3 and sum(d>.25 for d in differences)>=3:
            return True
        return None

    def _observe_frame(self, frame):
        rgb=np.asarray(frame)
        if rgb.shape!=(720,1280,3):
            raise ValueError('RookieArenaVision requires normalized RGB 1280x720x3')
        gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
        result=dict(screen=None,flags=None,failed=set(),signature=None,auto_on=None,
                    friendship_available=None,friendship_affordable=None,
                    skystone_affordable=None,selected_currency=None,
                    selected_opponent=None,challenge_enabled=False,confirm_visible=False)
        # Refresh is a separate modal; never act on the dimmed list behind it.
        if (self._match(gray,'refresh_title',(550,185,730,245))
                and self._match(gray,'refresh_question',(440,260,840,315))):
            result['screen']='refresh'
            result['refresh_free']=bool(
                self._match(gray,'refresh_free_notice',(380,375,900,435))
                and self._match(gray,'refresh_free_cost',(650,475,725,525)))
            result['refresh_remaining']=None
            if (not result['refresh_free']
                    and self._match(gray,'refresh_daily',(430,355,830,405))
                    and self._match(gray,'refresh_remaining',(480,395,720,440))):
                remaining=self._number(rgb[400:430,713:743])
                if remaining is not None and 0 <= remaining <= 30:
                    result['refresh_remaining']=remaining
            result['refresh_confirm_visible']=self._match(gray,'refresh_confirm',(755,470,875,530))
            return result
        # Friendship can cover Victory and its Confirm; close the overlay first.
        if (self._match(gray,'friendship_level_title',(510,130,1005,205))
                and self._match(gray,'friendship_level_close',(665,525,850,625))):
            result['screen']='friendship'
            return result
        # Promotion overlays sit on top of the battle/result screen. Recognize
        # their own controls before considering anything visible behind them.
        if (self._match(gray,'promotion_rewards',(475,145,805,220))
                and self._match(gray,'promotion_close',(550,490,730,590))):
            result['screen']='promotion_rewards'
            return result
        if (self._match(gray,'promotion_confirm',(550,615,745,705))
                and self._match(gray,'promotion_marker',(580,395,700,455))):
            result['screen']='promotion'
            return result
        if self._match(gray,'purchase',(505,128,770,192)):
            result['screen']='purchase'
            available=self._match(gray,'friendship',(382,307,476,390),.76)
            cooldown=self._match(gray,'cooldown',(400,307,630,361),.78)
            result['friendship_available']=True if available else False if cooldown else None
            # Read digits only, excluding Owned and the cost labels.
            friendship=self._number(rgb[407:435,425:610],True,True) if available else None
            skystone=self._number(rgb[407:435,710:870],True,True)
            result['friendship_affordable']=friendship>=100 if friendship is not None else None
            result['skystone_affordable']=skystone>=30 if skystone is not None else None
            # A selected card has a bright yellow border. Its unselected peer does not.
            for currency,x in (('friendship',380),('skystone',667)):
                strip=rgb[315:425,x:x+8].astype(float)
                yellow=((strip[:,:,0]>175)&(strip[:,:,1]>170)&(strip[:,:,2]<170)) | (
                    (strip[:,:,0]>160)&(strip[:,:,1]>150)&(strip[:,:,2]<strip[:,:,0]*.9))
                if np.count_nonzero(yellow)>90:
                    result['selected_currency']=currency
            return result
        for screen in ('victory','defeat'):
            if self._match(gray,screen,(435,200,835,290),.78):
                result['screen']=screen
                result['confirm_visible']=self._match(gray,'confirm',(1090,620,1250,700),.78)
                return result
        if self._match(gray,'title',(50,8,265,60)):
            # The header becomes "N Consecutive Victories!" after a win.
            # The opponent-selection prompt remains present in both layouts.
            if self._match(gray,'list_prompt',(490,560,810,620)):
                result['screen']='list'
                # Numerator ends before the dim slash; denominator is deliberately excluded.
                # Keep the raised purchase '+' above the digit baseline out
                # of OCR; at some window sizes it is tall enough to be a glyph.
                # Header resources shift horizontally with the current layout.
                # Locate the fixed /5 suffix before reading its numerator.
                suffix=self.templates['flags_denominator']
                region=gray[20:52,490:610]
                _,score,_,(sx,sy)=cv2.minMaxLoc(cv2.matchTemplate(region,suffix,cv2.TM_CCOEFF_NORMED))
                if score>=.90:
                    right=490+sx+2
                    result['flags']=self._flags(rgb[24:50,right-36:right])
                    result['purchase_open_point']=(490+sx-22,18)
                else:
                    result['flags']=self._flags(rgb[24:50,530:566])
                for row,y in enumerate((172,300,428),1):
                    patch=rgb[y+12:y+85,925:970].astype(float)
                    red=(patch[:,:,0]>35)&(patch[:,:,0]>patch[:,:,1]*1.7)&(patch[:,:,0]>patch[:,:,2]*1.4)
                    if red.mean()>.60:
                        result['failed'].add(row)
                # Portrait interiors avoid the yellow selection strip and red row background.
                patches=[gray[y:y+40,588:884].copy() for y in (205,333,461)]
                same=self._roster is not None and all(
                    cv2.minMaxLoc(cv2.matchTemplate(gray[y-10:y+50,578:894],t,cv2.TM_CCOEFF_NORMED))[1]>.78
                    for y,t in zip((205,333,461),self._roster))
                if not same:
                    self._roster=patches
                    self._signature=hashlib.sha256(np.concatenate(patches).tobytes()).hexdigest()
                result['signature']=self._signature
                for row,y in enumerate((267,395,523),1):
                    strip=rgb[y-8:y+9,400:920].astype(float)
                    gold=(strip[:,:,0]>140)&(strip[:,:,1]>100)&(strip[:,:,2]<90)
                    if gold.mean()>.30:
                        result['selected_opponent']=row
                button=rgb[643:689,540:740].astype(float)
                result['challenge_enabled']=bool(((button[:,:,1]>55)&(button[:,:,1]>button[:,:,0]*1.35)).mean()>.30)
            elif self._match(gray,'team',(470,505,650,580),.70) and self._match(gray,'start',(790,625,900,700)):
                result['screen']='team'
            return result
        if self._match(gray,'battle',(570,0,705,100),.75):
            result['screen']='battle'
            # Auto's visible HUD has four small portraits on blue bases, each
            # with the same white checkmark. Blue skill effects/animations alone
            # must not confirm auto: the rotating A also passes its idle pose.
            portraits=[]
            checked=[]
            blue_slots=[]
            for x in (1004,1082,1160,1238):
                base=rgb[681:715,x-17:x+18].astype(float)
                r,g,b=base.transpose(2,0,1)
                blue=(b>100)&(b>r*1.5)&(b>g*1.1)
                blue_slots.append(blue.mean()>.45)
                tick=blue.mean()>.45 and self._match(gray,'auto_check',(x-20,679,x+20,715),.78)
                checked.append(tick)
                # Dead party members keep their small auto HUD slot but lose
                # its blue base/checkmark. Require both a red portrait and the
                # dark Skill label above it, alongside surviving checked slots.
                red=(r>65)&(r>g*1.5)&(r>b*1.4)
                dead=red.mean()>.40 and self._match(
                    gray,'auto_dead_label',(x-27,610,x+27,653),.85,brightness_floor=10)
                portraits.append(tick or dead)
            # Manual uses three large square skills instead of four portraits.
            # Require those controls as well as the idle icon, leaving hidden
            # HUDs during opening/skill animations unknown.
            manual=[any(self._manual_slot(rgb,gray,x+offset)
                        for offset in (0,-4,-8,4))
                    for x in (977,1080,1183)]
            if all(portraits) and any(checked):
                result['auto_on']=True
            elif (not all(blue_slots) and not any(checked) and all(manual)
                  and self._match(gray,'auto_off',(1090,0,1160,70),.91)):
                result['auto_on']=False
        return result
