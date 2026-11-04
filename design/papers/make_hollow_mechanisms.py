#!/usr/bin/env python3
"""Depth identities and width replicas, based on Hollow-LLM §§4.2–4.3.

Original vector schematics. The width example has two replicas and an untied
decoder; preserving logits requires the paper's compatible arithmetic, weights,
normalization and positional encoding. No external packages required.
"""
from make_figures import Figure, INK, MUTED, GOLD, RULE, GRAY, WARM


def add_node(f, x, y):
    f.parts.append(f'<circle cx="{x}" cy="{y}" r="20" fill="white" stroke="{INK}" stroke-width="1.7"/>')
    f.text(x, y+8, '+', 29, INK, anchor='middle')


def bypass(f, points):
    coords = ' '.join(('M' if i == 0 else 'L')+str(x)+' '+str(y) for i,(x,y) in enumerate(points))
    f.parts.append(f'<path d="{coords}" fill="none" stroke="{MUTED}" stroke-width="1.7" marker-end="url(#arrow)"/>')


def draw(mobile=False):
    f=Figure(450 if mobile else 900,1040 if mobile else 650,'Hollow-LLM depth and width constructions',
      'Depth hollowing appends residual blocks whose attention and FFN outputs are zero, so x plus zero plus zero equals x. '
      'Width hollowing repeats compatible hidden states. With two copies and an untied decoder D prime equal to [D/2,D/2], '
      'the expanded state [h,h] produces the same logits Dh. Coordinated parameters and arithmetic are required.')
    if not mobile:
        f.text(28,34,'Two ways to add ghost weights',25,bold=True)
        f.text(28,84,'A. Depth: added blocks are exact identities',23,bold=True)
        for x in (28,402,804):
            f.box(x,175,72 if x!=804 else 68,70,WARM,GOLD)
            f.text(x+(36 if x!=804 else 34),220,'x',29,GOLD,True,anchor='middle')
        for x,label in ((142,'Attention'),(516,'FFN')):
            f.box(x,165,176,90,GRAY,MUTED)
            f.text(x+20,199,label,21,bold=True)
            f.text(x+20,230,'output = 0',20)
        for x1,x2 in ((100,132),(318,338),(382,392),(474,506),(692,712),(756,794)):
            f.line(x1,210,x2,210,MUTED,True)
        add_node(f,360,210);add_node(f,734,210)
        bypass(f,[(118,210),(118,128),(360,128),(360,188)])
        bypass(f,[(490,210),(490,128),(734,128),(734,188)])
        f.text(225,115,'residual path',17,MUTED,anchor='middle')
        f.text(610,115,'residual path',17,MUTED,anchor='middle')
        f.text(28,295,'x + 0 + 0 = x. The active inner-model layers are retained.',21)
        f.line(28,332,872,332)
        f.text(28,378,'B. Width: replicate coordinates; preserve logits',23,bold=True)
        f.text(28,412,'Two replicas with an untied decoder',19,MUTED)
        f.box(28,458,96,74,WARM,GOLD)
        f.text(76,504,'h',29,GOLD,True,anchor='middle')
        f.line(129,495,180,495,MUTED,True)
        f.box(192,445,192,100,WARM,GOLD)
        f.line(288,445,288,545,GOLD)
        f.text(240,504,'h',29,GOLD,True,anchor='middle')
        f.text(336,504,'h',29,GOLD,True,anchor='middle')
        f.text(288,575,'[h, h]',21,MUTED,anchor='middle')
        f.line(390,495,440,495,MUTED,True)
        f.box(452,445,230,100,GRAY,MUTED)
        f.text(567,482,'Adjusted decoder',21,bold=True,anchor='middle')
        f.text(567,519,'D′ = [D/2, D/2]',23,anchor='middle')
        f.line(688,495,740,495,MUTED,True)
        f.box(752,458,120,74,WARM,GOLD)
        f.text(812,504,'Dh',29,GOLD,True,anchor='middle')
        f.text(812,575,'Same logits',20,MUTED,anchor='middle')
        f.text(28,621,'Coordinated weights, normalization, and positional encoding are required.',19,MUTED)
    else:
        f.text(20,32,'Depth and width hollowing',24,bold=True)
        f.text(20,74,'A. Added residual identity blocks',21,bold=True)
        f.box(180,92,90,44,WARM,GOLD)
        f.text(225,123,'x',27,GOLD,True,anchor='middle')
        f.line(225,136,225,158,MUTED,True)
        for y,label in ((170,'Attention output = 0'),(332,'FFN output = 0')):
            f.box(105,y,240,70,GRAY,MUTED)
            f.text(225,y+43,label,21,bold=True,anchor='middle')
        f.line(225,240,225,254,MUTED,True)
        add_node(f,225,276)
        bypass(f,[(225,148),(54,148),(54,276),(203,276)])
        f.line(225,298,225,320,MUTED,True)
        f.line(225,402,225,421,MUTED,True)
        add_node(f,225,443)
        bypass(f,[(225,308),(54,308),(54,443),(203,443)])
        f.line(225,465,225,483,MUTED,True)
        f.box(180,495,90,50,WARM,GOLD)
        f.text(225,529,'x',27,GOLD,True,anchor='middle')
        f.text(225,579,'x + 0 + 0 = x',22,anchor='middle')
        f.line(20,607,430,607)
        f.text(20,649,'B. Two replicas, same logits',22,bold=True)
        f.box(20,678,96,52,WARM,GOLD)
        f.text(68,713,'h',27,GOLD,True,anchor='middle')
        f.line(122,704,160,704,MUTED,True)
        f.box(172,668,258,72,WARM,GOLD)
        f.line(301,668,301,740,GOLD)
        f.text(236,713,'h',27,GOLD,True,anchor='middle')
        f.text(365,713,'h',27,GOLD,True,anchor='middle')
        f.line(301,745,301,773,MUTED,True)
        f.box(20,785,410,82,GRAY,MUTED)
        f.text(225,817,'Adjusted untied decoder',21,bold=True,anchor='middle')
        f.text(225,848,'D′ = [D/2, D/2]',23,anchor='middle')
        f.line(225,872,225,899,MUTED,True)
        f.text(225,935,'D′[h, h] = Dh',27,GOLD,True,anchor='middle')
        f.text(20,991,['Coordinated weights, normalization,','and positional encoding are required.'],19,MUTED,leading=28)
    f.save('hollow-llm-mechanisms'+('-mobile' if mobile else '')+'.svg')


if __name__=='__main__':
    draw();draw(True)
    print('Wrote desktop and mobile Hollow-LLM mechanism figures.')
