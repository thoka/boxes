#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2013-2014 Florian Festi, 2019 Thomas Kalka
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Lernkartenkasten für Lotte
# this is a slightly changed dividertray

from boxes import Boxes, edges, boolarg
import math


from boxes.generators.dividertray import DividerTray,SlottedEdgeDescriptions,StraightEdgeDescription,SlotDescription,DividerSlotsEdge

class FlashCardBox(DividerTray):
    """Flashcard box - box with finger holes , slides for dividers and dividers"""

    ui_group = "Box"

    def __init__(self):
        Boxes.__init__(self)
        self.buildArgParser("x", "sy", "h","outside" )
        self.argparser.set_defaults(outside=False)
        self.argparser.set_defaults(reference=False)
        self.argparser.add_argument(
            "--slot_depth", type=float, default=20, help="depth of the slot in mm"
        )
        self.argparser.add_argument(
            "--slot_angle",
            type=float,
            default=0,
            help="angle at which slots are generated, in degrees. 0° is vertical.",
        )
        self.argparser.add_argument(
            "--slot_radius",
            type=float,
            default=2,
            help="radius of the slot entrance in mm",
        )
        self.argparser.add_argument(
            "--slot_extra_slack",
            type=float,
            default=0.2,
            help="extra slack (in addition to thickness and kerf) for slot width to help insert dividers",
        )
        self.argparser.add_argument(
            "--divider_bottom_margin",
            type=float,
            default=0,
            help="margin between box's bottom and divider's",
        )
        self.argparser.add_argument(
            "--divider_upper_notch_radius",
            type=float,
            default=1,
            help="divider's notch's upper radius",
        )
        self.argparser.add_argument(
            "--divider_lower_notch_radius",
            type=float,
            default=8,
            help="divider's notch's lower radius",
        )
        self.argparser.add_argument(
            "--divider_notch_depth",
            type=float,
            default=15,
            help="divider's notch's depth",
        )

    def render(self):
        self.left_wall = True
        self.right_wall = True
        self.sx = [self.x]

        side_walls_number = len(self.sx) - 1 + sum([self.left_wall, self.right_wall])
        assert (
            side_walls_number > 0
        ), "You need at least one side wall to generate this tray"

        slot_descriptions = self.generate_slot_descriptions(self.sy)

        if self.outside:
            self.sx = self.adjustSize(self.sx, self.left_wall, self.right_wall)
            side_wall_target_length = sum(self.sy) - 2 * self.thickness
            slot_descriptions.adjust_to_target_length(side_wall_target_length)
        else:
            # If the parameter 'h' is the inner height of the content itself,
            # then the actual tray height needs to be adjusted with the angle
            self.h = self.h * math.cos(math.radians(self.slot_angle))

        self.ctx.save()

        # Facing walls (outer) with finger holes to support side walls
        facing_wall_length = sum(self.sx) + self.thickness * (len(self.sx) - 1)
        side_edge = lambda with_wall: "F" if with_wall else "e"

        fe = FingerholeEdge(self)

        for _ in range(2):
            self.rectangularWall(
                facing_wall_length,
                self.h,
                ["F", side_edge(self.right_wall), fe, side_edge(self.left_wall)],
                callback=[self.generate_finger_holes],
                move="right",
            )

        # Side walls (outer & inner) with slots to support dividers
        side_wall_length = slot_descriptions.total_length()
        for _ in range(side_walls_number):
            se = DividerSlotsEdge(self, slot_descriptions.descriptions)
            fe = se # FingeredEdge(self)
            self.rectangularWall(
                side_wall_length, self.h, ["f", "f", se, "f"], move="up"
            )

        # Bottom 
        self.rectangularWall(
            side_wall_length,self.sx[0],
            ["F","f","F","f"],
            move="up",
        )


        # Switch to right side of the file
        #self.ctx.restore()
        #self.rectangularWall(
        #    max(facing_wall_length, side_wall_length), self.h, "ffff", move="right only"
        #)

        # Dividers
        divider_height = (
            # h, with angle adjustement
            self.h / math.cos(math.radians(self.slot_angle))
            # removing what exceeds in the width of the divider
            - self.thickness * math.tan(math.radians(self.slot_angle))
            # with margin
            - self.divider_bottom_margin
        )
        for i, length in enumerate(self.sx):
            is_first_wall = i == 0
            is_last_wall = i == len(self.sx) - 1
            self.generate_divider(
                length,
                divider_height,
                "up",
                only_one_wall=(is_first_wall and not self.left_wall)
                or (is_last_wall and not self.right_wall),
            )

        if self.debug:
            debug_info = ["Debug"]
            debug_info.append(
                "Slot_edge_outer_length:{0:.2f}".format(
                    slot_descriptions.total_length() + 2 * self.thickness
                )
            )
            debug_info.append(
                "Slot_edge_inner_lengths:{0}".format(
                    str.join(
                        "|",
                        [
                            "{0:.2f}".format(e.usefull_length())
                            for e in slot_descriptions.get_straigth_edges()
                        ],
                    )
                )
            )
            debug_info.append(
                "Face_edge_outer_length:{0:.2f}".format(
                    facing_wall_length
                    + self.thickness * sum([self.left_wall, self.right_wall])
                )
            )
            debug_info.append(
                "Face_edge_inner_lengths:{0}".format(
                    str.join("|", ["{0:.2f}".format(e) for e in self.sx])
                )
            )
            debug_info.append("Tray_height:{0:.2f}".format(self.h))
            debug_info.append(
                "Content_height:{0:.2f}".format(
                    self.h / math.cos(math.radians(self.slot_angle))
                )
            )
            self.text(str.join("\n", debug_info), x=5, y=5, align="bottom left")

    def generate_slot_descriptions(self, sections):
        slot_width = self.thickness + self.slot_extra_slack

        descriptions = SlottedEdgeDescriptions()

        # Special case: if first slot start at 0, then radius is 0
        first_correction = 0
        current_section = 0
        if sections[0] == 0:
            slot = SlotDescription(
                slot_width,
                depth=self.slot_depth,
                angle=self.slot_angle,
                start_radius=0,
                end_radius=self.slot_radius,
            )
            descriptions.add(slot)
            first_correction = slot.round_edge_end_correction()
            current_section += 1

        first_length = sections[current_section]
        current_section += 1
        descriptions.add(
            StraightEdgeDescription(
                first_length, round_edge_compensation=first_correction
            )
        )

        for l in sections[current_section:]:
            slot = SlotDescription(
                slot_width,
                depth=self.slot_depth,
                angle=self.slot_angle,
                radius=self.slot_radius,
            )

            # Fix previous edge length
            previous_edge = descriptions.get_last_edge()
            previous_edge.round_edge_compensation += slot.round_edge_start_correction()

            # Add this slot
            descriptions.add(slot)

            # Add the straigth edge after this slot
            descriptions.add(
                StraightEdgeDescription(l, slot.round_edge_end_correction())
            )

        # We need to add extra space for the divider (or the actual content)
        # to slide all the way down to the bottom of the tray in spite of walls
        end_length = self.h * math.tan(math.radians(self.slot_angle))
        descriptions.get_last_edge().angle_compensation += end_length

        return descriptions

class FingerholeEdge(edges.BaseEdge):
    """Edge with multiple angled rounded slots for dividers"""

    description = "Edge with one fingerhole"

    def __init__(self, boxes):
        super(FingerholeEdge, self).__init__(boxes, None)

    def __call__(self, width, **kw):

        #self.ctx.save()
        b = self.boxes
        upper_radius = self.divider_upper_notch_radius
        lower_radius = self.divider_lower_notch_radius
        upper_third = (width - 2 * upper_radius - 2 * lower_radius) / 3

        # Upper: divider width (with notch if possible)
        if upper_third > 0:
            self.edge(upper_third)
            self.corner(90, upper_radius)
            self.edge(self.divider_notch_depth - upper_radius - lower_radius)
            self.corner(-90, lower_radius)
            self.edge(upper_third)
            self.corner(-90, lower_radius)
            self.edge(self.divider_notch_depth - upper_radius - lower_radius)
            self.corner(90, upper_radius)
            self.edge(upper_third)
        else:
            # if there isn't enough room for the radius, we don't use it
            self.edge(width)

        # rounding errors might accumulates :
        # restore context and redo the move straight
        #self.ctx.restore()
        #self.moveTo(length)
